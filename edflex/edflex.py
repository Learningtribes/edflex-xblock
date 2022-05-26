import logging
import pkg_resources

from web_fragments.fragment import Fragment

from xblock.core import XBlock
from xblock.fields import String, Scope, Dict, Float
from xblockutils.resources import ResourceLoader
from xblockutils.studio_editable import StudioEditableXBlockMixin

from .api import EdflexOauthClient
from .models import Category, Resource
from .utils import get_edflex_configuration_for_org

# Make '_' a no-op so we can scrape strings
_ = lambda text: text

log = logging.getLogger('edflex_xblock')
loader = ResourceLoader(__name__)


class EdflexXBlock(StudioEditableXBlockMixin, XBlock):

    display_name = String(
        scope=Scope.settings,
        default=_("Currated Content")
    )
    format = String(scope=Scope.settings)
    category = String(scope=Scope.settings)
    catalog = String(scope=Scope.settings)
    language = String(scope=Scope.settings)
    resource = Dict(scope=Scope.settings)
    weight = Float(
        default=1.0,
        scope=Scope.settings,
    )
    score = Float(
        default=0,
        scope=Scope.user_state,
    )
    icon_class = 'problem'
    count_stars = 5
    has_score = True
    has_author_view = True
    editable_fields = ['format', 'category', 'catalog', 'language', 'resource', 'weight']

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def student_view(self, context=None):
        """
        The primary view of the EdflexXBlock, shown to students
        when viewing courses.
        """
        if context is None:
            context = {}

        context.update({
            'svg_sprite': self.resource_string('public/images/sprite.svg'),
        })

        self.update_student_context(context)
        fragment = Fragment()
        fragment.content = loader.render_django_template('static/html/edflex.html', context)
        fragment.add_css(self.resource_string("static/css/edflex.css"))

        if self.resource.get('type', '') == 'video':
            fragment.add_javascript_url('https://www.youtube.com/iframe_api')

        fragment.add_javascript(loader.load_unicode('static/js/src/parse_duration.js'))
        fragment.add_javascript(self.resource_string("static/js/src/edflex.js"))
        fragment.initialize_js('EdflexXBlock')
        return fragment

    def update_student_context(self, context):
        note = self.resource.get('note', {}) or {}
        full_stars = int(note.get('global', 0))
        empty_stars = int(self.count_stars - note.get('global', 0))
        half_stars = int(self.count_stars - full_stars - empty_stars)
        context.update({
            'resource': self.resource,
            'score': self.score,
            'stars': {
                'average': note.get('global', '-'),
                'full': range(full_stars),
                'empty': range(empty_stars),
                'half': range(half_stars),
                'total_reviews': note.get('total_reviews')
            }
        })
        return context

    def author_view(self, context=None):
        context.update({
            'svg_sprite': self.resource_string('public/images/sprite.svg'),
            'resource': self.resource,
        })
        html = loader.render_django_template("static/html/author_view.html", context)
        fragment = Fragment(html)
        fragment.add_css(self.resource_string("static/css/edflex.css"))
        return fragment

    def studio_view(self, context):
        """
        Render a form for editing this XBlock
        """
        init_values = {
            'format': self.format,
            'category': self.category,
            'catalog': self.catalog,
            'language': self.language,
            'resource': self.resource,
        }
        context.update({
            'svg_sprite': self.resource_string('public/images/sprite.svg'),
        })
        self.update_studio_context(context)
        fragment = Fragment()
        fragment.content = loader.render_django_template('static/html/studio_edit.html', context)
        fragment.add_css(self.resource_string("static/css/edflex.css"))
        fragment.add_css(self.resource_string("static/css/select2.css"))
        fragment.add_javascript(loader.load_unicode('static/js/src/parse_duration.js'))
        fragment.add_javascript(loader.load_unicode('static/js/src/studio_edit.js'))
        fragment.initialize_js(
            'StudioEditableEdflexXBlock',
            json_args={
                'url_select2': self.runtime.local_resource_url(self, 'public/js/select2.min'),
                'init_values': init_values
            }
        )
        return fragment

    def update_studio_context(self, context):
        edflex_client = EdflexOauthClient(get_edflex_configuration_for_org(self.location.org))
        r_catalogs = edflex_client.get_catalogs()
        catalog_ids = [r_catalog['id'] for r_catalog in r_catalogs]
        categories = Category.objects.filter(
            resources__catalog_id__in=catalog_ids
        ).order_by(
            'catalog_title',
            'name'
        ).distinct().values()
        languages = Resource.objects.filter(
            catalog_id__in=catalog_ids,
            language__isnull=False
        ).order_by(
            'language'
        ).values_list(
            'language', flat=True
        ).distinct()

        context.update({
            'categories': categories,
            'languages': languages,
            'weight': self.weight,
        })
        return context

    @XBlock.json_handler
    def get_list_resources(self, data, suffix=''):
        r_type = data.get('format')
        category_id = data.get('category_id')
        language = data.get('language')

        if not r_type:
            return {'resources': []}

        edflex_client = EdflexOauthClient(get_edflex_configuration_for_org(self.location.org))
        r_catalogs = edflex_client.get_catalogs()
        catalog_ids = [r_catalog['id'] for r_catalog in r_catalogs]
        resources = Resource.objects.filter(
            r_type=r_type,
        )

        if category_id:
            try:
                category = Category.objects.get(id=category_id)
            except (Category.DoesNotExist, ValueError) as er:
                log.error(er)
                resources = resources.filter(
                    catalog_id__in=catalog_ids,
                )
            else:
                resources = resources.filter(
                    categories__id=category.id,
                    catalog_id=category.catalog_id
                )
        else:
            resources = resources.filter(
                catalog_id__in=catalog_ids,
            )

        if language:
            resources = resources.filter(
                language=language
            )

        return {
            'resources': list(resources.distinct().order_by('title').values('resource_id', 'title'))
        }

    @XBlock.json_handler
    def get_resource(self, data, suffix=''):
        resource_id = data.get('resource')
        edflex_client = EdflexOauthClient(get_edflex_configuration_for_org(self.location.org))
        resource = edflex_client.get_resource(resource_id)
        return resource

    @XBlock.json_handler
    def set_grade(self, data, suffix=''):
        score = data.get('score', 1)

        if score > self.score:
            self.score = score
            self.publish_grade()

        return {'status': 'ok'}

    def max_score(self):
        """
        Return the maximum score possible.
        """
        return self.weight

    def publish_grade(self):
        self.runtime.publish(
            self,
            'grade',
            {
                'value': self.score * self.weight,
                'max_value': self.weight,
            })

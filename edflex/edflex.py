import logging
import pkg_resources

from web_fragments.fragment import Fragment

from xblock.core import XBlock
from xblock.fields import String, Scope, Dict, List, Float
from xblockutils.resources import ResourceLoader
from xblockutils.studio_editable import StudioEditableXBlockMixin

from .api import EdflexOauthClient
from .models import Category, Resource
from .utils import get_edflex_configuration_for_org

# Make '_' a no-op so we can scrape strings
_ = lambda text: text

log = logging.getLogger(__name__)
loader = ResourceLoader(__name__)


class EdflexXBlock(StudioEditableXBlockMixin, XBlock):

    display_name = String(
        scope=Scope.settings,
        default=_("External Resource")
    )
    format = String(scope=Scope.settings)
    category = String(scope=Scope.settings)
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

    has_author_view = True
    editable_fields = ['format', 'category', 'language', 'resource', 'weight']

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def student_view(self, context=None):
        """
        The primary view of the EdflexXBlock, shown to students
        when viewing courses.
        """
        html = self.resource_string("static/html/edflex.html")
        frag = Fragment(html.format(self=self))
        frag.add_css(self.resource_string("static/css/edflex.css"))
        frag.add_javascript(self.resource_string("static/js/src/edflex.js"))
        frag.initialize_js('EdflexXBlock')
        return frag

    def author_view(self, context=None):
        html = loader.render_django_template("static/html/author_view.html", context)
        frag = Fragment(html)
        return frag

    def studio_view(self, context):
        """
        Render a form for editing this XBlock
        """
        init_values = {
            'format': self.format,
            'category': self.category,
            'language': self.language,
            'resource': self.resource,
        }
        self.update_studio_context(context)
        fragment = Fragment()
        fragment.content = loader.render_template('static/html/studio_edit.html', context)
        fragment.add_css(self.resource_string("static/css/edflex.css"))
        fragment.add_css(self.resource_string("static/css/select2.css"))
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
        category = data.get('category')
        language = data.get('language')

        if not (r_type or category):
            return {'resources': []}

        edflex_client = EdflexOauthClient(get_edflex_configuration_for_org(self.location.org))
        r_catalogs = edflex_client.get_catalogs()
        catalog_ids = [r_catalog['id'] for r_catalog in r_catalogs]
        resources = Resource.objects.filter(
            catalog_id__in=catalog_ids,
            r_type=r_type,
            categories__category_id=category
        )

        if language:
            resources = resources.filter(
                language=language
            )

        return {
            'resources': list(resources.distinct().values('resource_id', 'title'))
        }

    @XBlock.json_handler
    def get_resource(self, data, suffix=''):
        resource_id = data.get('resource')
        edflex_client = EdflexOauthClient(get_edflex_configuration_for_org(self.location.org))
        resource = edflex_client.get_resource(resource_id)
        return resource

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
                'value': self.score,
                'max_value': self.weight,
            })

import logging
import pkg_resources

from web_fragments.fragment import Fragment

from xblock.core import XBlock
from xblock.fields import String, Scope, Dict
from xblockutils.resources import ResourceLoader
from xblockutils.studio_editable import StudioEditableXBlockMixin

from .api import EdflexOauthClient
from .models import Category, Resource
from .utils import get_edflex_configuration

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

    has_author_view = True

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
        self.update_studio_context(context)
        fragment = Fragment()
        fragment.content = loader.render_template('static/html/studio_edit.html', context)
        fragment.add_javascript(loader.load_unicode('static/js/src/studio_edit.js'))
        fragment.initialize_js('StudioEditableEdflexXBlock')
        return fragment

    def update_studio_context(self, context):
        edflex_client = EdflexOauthClient(get_edflex_configuration())
        r_catalogs = edflex_client.get_catalogs()
        catalog_ids = [r_catalog['id'] for r_catalog in r_catalogs]
        categories = Category.objects.filter(
            resources__catalog_id__in=catalog_ids
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
            'languages': languages
        })
        return context

from .model import AddonBitbucketUserSettings, AddonBitbucketNodeSettings
from .routes import settings_routes, page_routes

MODELS = [AddonBitbucketUserSettings, AddonBitbucketNodeSettings]
USER_SETTINGS_MODEL = AddonBitbucketUserSettings
NODE_SETTINGS_MODEL = AddonBitbucketNodeSettings

ROUTES = [settings_routes, page_routes]

SHORT_NAME = 'bitbucket'
FULL_NAME = 'Bitbucket'

OWNERS = ['user', 'node']

ADDED_DEFAULT = []
ADDED_MANDATORY = []

VIEWS = ['widget', 'page']
CONFIGS = ['user', 'node']

CATEGORIES = ['storage']

INCLUDE_JS = {
    'widget': [],
    'page': [],
}

INCLUDE_CSS = {
    'widget': [],
    'page': ['/static/css/hgrid-base.css'],
}

WIDGET_HELP = 'Bitbucket Add-on Alpha'

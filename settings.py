from os import environ

SESSION_CONFIGS = [
        dict(name='FullExperiment', app_sequence=['Introduction','Chat',"Evaluation","Outro"], num_demo_participants=10,prolific_return_code='xxxx',prolific_return_url='https://www.prolific.com/xxx'),
        dict(name='Introduction', app_sequence=['Introduction'], num_demo_participants=1),
        dict(name='Chat', app_sequence=['Chat'], num_demo_participants=1),
        dict(name='Evaluation', app_sequence=['Evaluation'], num_demo_participants=1),
        dict(name='Outro', app_sequence=['Outro'], num_demo_participants=1,prolific_return_code='xxxx',prolific_return_url='https://www.prolific.com/xxx'),
]

# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00, participation_fee=0.00, doc=""
)

PARTICIPANT_FIELDS = []
SESSION_FIELDS = ['ProlificID']

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'en'

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = True

ADMIN_USERNAME = 'admin'
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """ """

SECRET_KEY = '5002814748463'
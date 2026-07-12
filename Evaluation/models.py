from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
)

from settings import LANG

doc = """
    Post-Study Questionnaire. Items adapted from the validated WAI-SR and UEQ+
    instruments (see field-level comments below for subscale/source detail).

    Covers: WAI-SR working-alliance subscales (Goal/Task/Bond), UEQ+ response
    behaviour/quality/usefulness (semantic differential), a researcher-developed
    personalization manipulation check, perceived AI hallucination, and open
    feedback. Superseded by this file: the old Big-Five/ERQ trait-paragraph
    evaluation (useful/plausible/trustworthy/accurate), which measured the
    original CHI Mixed Profiling paper's DVs, not this study's.
"""

# ---------------------------------------------------------------------------
# WAI-SR — Goal / Task / Bond ("Nie" 1 .. "Immer" 7)
# This is the original validated WAI-SR frequency scale — do not change to an
# agreement scale, even though the statement wording looks agreement-style.
# ---------------------------------------------------------------------------
WAI_CHOICES_DE = [[1, "Nie"], [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"], [7, "Immer"]]
WAI_CHOICES_EN = [[1, "Never"], [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"], [7, "Always"]]
WAI_CHOICES = WAI_CHOICES_DE if LANG == 'de' else WAI_CHOICES_EN

WAI_GOAL_FIELDS_DE = [
    ('wai_goal_1', "Der KI-Coach und ich hatten ein gemeinsames Verständnis vom Ziel der Sitzung."),
    ('wai_goal_2', "Der KI-Coach hat sich auf das konzentriert, was für mich wichtig war zu bearbeiten."),
    ('wai_goal_3', "Die Sitzung hat mir geholfen zu klären, welche emotionale Veränderung für mich hilfreich wäre."),
]
WAI_GOAL_FIELDS_EN = [
    ('wai_goal_1', "The AI coach and I had a shared understanding of the goal of the session."),
    ('wai_goal_2', "The AI coach focused on what was important for me to work on."),
    ('wai_goal_3', "The session helped clarify what kind of emotional change would be helpful for me."),
]
WAI_GOAL_FIELDS = WAI_GOAL_FIELDS_DE if LANG == 'de' else WAI_GOAL_FIELDS_EN

WAI_TASK_FIELDS_DE = [
    ('wai_task_1', "Die vom KI-Coach vorgeschlagenen Schritte erschienen mir geeignet, um meine emotionale Situation zu verbessern."),
    ('wai_task_2', "Ich war zuversichtlich, dass die Übungen in der Sitzung nützlich sind."),
    ('wai_task_3', "Durch die Sitzung ist mir klarer geworden, wie ich meine Emotionen regulieren könnte."),
]
WAI_TASK_FIELDS_EN = [
    ('wai_task_1', "The steps suggested by the AI coach seemed appropriate for improving my emotional situation."),
    ('wai_task_2', "I felt confident about the usefulness of the activities in the session."),
    ('wai_task_3', "As a result of the session, I am clearer about how I might regulate my emotions."),
]
WAI_TASK_FIELDS = WAI_TASK_FIELDS_DE if LANG == 'de' else WAI_TASK_FIELDS_EN

WAI_BOND_FIELDS_DE = [
    ('wai_bond_1', "Ich hatte das Gefühl, dass der KI-Coach verstanden hat, was ich versucht habe auszudrücken."),
    ('wai_bond_2', "Die Interaktion mit dem KI-Coach fühlte sich respektvoll an."),
    ('wai_bond_3', "Ich fühlte mich wohl dabei, mich auf die Anleitung des KI-Coaches zu verlassen."),
]
WAI_BOND_FIELDS_EN = [
    ('wai_bond_1', "I felt that the AI coach understood what I was trying to express."),
    ('wai_bond_2', "The interaction with the AI coach felt respectful."),
    ('wai_bond_3', "I felt comfortable relying on the AI coach's guidance during the session."),
]
WAI_BOND_FIELDS = WAI_BOND_FIELDS_DE if LANG == 'de' else WAI_BOND_FIELDS_EN

# ---------------------------------------------------------------------------
# UEQ+ semantic-differential blocks (7-point, bipolar adjective pairs)
# ---------------------------------------------------------------------------
SEMANTIC_DIFFERENTIAL_SCALE = [i for i in range(1, 8)]

UEQ_BEHAVIOR_INTRO_DE = "Das Antwortverhalten des Sprachassistenten empfinde ich als …"
UEQ_BEHAVIOR_INTRO_EN = "In my opinion the response behaviour of the voice assistant is …"
UEQ_BEHAVIOR_INTRO = UEQ_BEHAVIOR_INTRO_DE if LANG == 'de' else UEQ_BEHAVIOR_INTRO_EN

UEQ_BEHAVIOR_FIELDS_DE = [
    ('ueq_behavior_1', "künstlich", "natürlich"),
    ('ueq_behavior_2', "unangenehm", "angenehm"),
    ('ueq_behavior_3', "unsympathisch", "sympathisch"),
    ('ueq_behavior_4', "langweilig", "unterhaltsam"),
]
UEQ_BEHAVIOR_FIELDS_EN = [
    ('ueq_behavior_1', "artificial", "natural"),
    ('ueq_behavior_2', "unpleasant", "pleasant"),
    ('ueq_behavior_3', "unlikeable", "likeable"),
    ('ueq_behavior_4', "boring", "entertaining"),
]
UEQ_BEHAVIOR_FIELDS = UEQ_BEHAVIOR_FIELDS_DE if LANG == 'de' else UEQ_BEHAVIOR_FIELDS_EN

UEQ_QUALITY_INTRO_DE = "Die Antworten des Sprachassistenten waren …"
UEQ_QUALITY_INTRO_EN = "The answers and responses given by the voice assistant are …"
UEQ_QUALITY_INTRO = UEQ_QUALITY_INTRO_DE if LANG == 'de' else UEQ_QUALITY_INTRO_EN

UEQ_QUALITY_FIELDS_DE = [
    ('ueq_quality_1', "unpassend", "passend"),
    ('ueq_quality_2', "nutzlos", "nützlich"),
    ('ueq_quality_3', "nicht hilfreich", "hilfreich"),
    ('ueq_quality_4', "unintelligent", "intelligent"),
]
UEQ_QUALITY_FIELDS_EN = [
    ('ueq_quality_1', "inappropriate", "suitable"),
    ('ueq_quality_2', "useless", "useful"),
    ('ueq_quality_3', "not helpful", "helpful"),
    ('ueq_quality_4', "unintelligent", "intelligent"),
]
UEQ_QUALITY_FIELDS = UEQ_QUALITY_FIELDS_DE if LANG == 'de' else UEQ_QUALITY_FIELDS_EN

# --- UEQ+ — Usefulness ------------------------------------------------------
UEQ_USEFUL_INTRO_DE = "Ich betrachte die Möglichkeit, das Produkt zu nutzen, als …"
UEQ_USEFUL_INTRO_EN = "I consider the possibility of using the product as …"
UEQ_USEFUL_INTRO = UEQ_USEFUL_INTRO_DE if LANG == 'de' else UEQ_USEFUL_INTRO_EN

UEQ_USEFUL_FIELDS_DE = [
    ('ueq_useful_1', "nutzlos", "nützlich"),
    ('ueq_useful_2', "nicht lohnend", "lohnend"),
    ('ueq_useful_3', "nicht hilfreich", "hilfreich"),
    ('ueq_useful_4', "nicht vorteilhaft", "vorteilhaft"),
]
UEQ_USEFUL_FIELDS_EN = [
    ('ueq_useful_1', "useless", "useful"),
    ('ueq_useful_2', "not rewarding", "rewarding"),
    ('ueq_useful_3', "not helpful", "helpful"),
    ('ueq_useful_4', "not beneficial", "beneficial"),
]
UEQ_USEFUL_FIELDS = UEQ_USEFUL_FIELDS_DE if LANG == 'de' else UEQ_USEFUL_FIELDS_EN

# NOTE: UEQ+ — Comprehensibility ("Verständlichkeit") is intentionally not
# implemented here: it's an STT/voice-recognition diagnostic, not tied to any
# research question.

# ---------------------------------------------------------------------------
# Personalization (manipulation check) — researcher-developed, not a validated
# scale. Manipulation check for H1/H2 (perceived personalization expected to
# be elevated in T2/T3).
# ---------------------------------------------------------------------------
PERSONALIZATION_CHOICES_DE = [[1, "Trifft gar nicht zu"], [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"], [7, "Trifft völlig zu"]]
PERSONALIZATION_CHOICES_EN = [[1, "Not at all true"], [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"], [7, "Completely true"]]
PERSONALIZATION_CHOICES = PERSONALIZATION_CHOICES_DE if LANG == 'de' else PERSONALIZATION_CHOICES_EN

PERSONALIZATION_FIELDS_DE = [
    ('pers_1', "Ich hatte das Gefühl, dass die Anleitung des KI-Coaches speziell auf mich und meine Situation zugeschnitten war."),
    ('pers_2', "Der KI-Coach schien meine persönlichen Eigenschaften zu kennen und zu berücksichtigen."),
    ('pers_3', "Die Sitzung fühlte sich eher allgemein als persönlich an."),
]
PERSONALIZATION_FIELDS_EN = [
    ('pers_1', "I felt that the AI coach's guidance was tailored specifically to me and my situation."),
    ('pers_2', "The AI coach seemed to know and take into account my personal characteristics."),
    ('pers_3', "The session felt generic rather than personal."),
]
PERSONALIZATION_FIELDS = PERSONALIZATION_FIELDS_DE if LANG == 'de' else PERSONALIZATION_FIELDS_EN

# Fields that must be reverse-scored at analysis time — see reverse_score().
# Raw values are stored exactly as answered; labels are NOT flipped in the UI.
REVERSE_SCORED_FIELDS = ['pers_3']


def reverse_score(raw_value, points=7):
    """Reverse-score a 7-point Likert response: score = points + 1 - raw_value.

    Apply only to fields listed in REVERSE_SCORED_FIELDS (currently: pers_3)
    when computing analysis-ready scores. Do not use this to alter the stored
    raw value or the displayed answer labels.
    """
    return points + 1 - raw_value


# ---------------------------------------------------------------------------
# Perceived AI Hallucination (exploratory)
# ---------------------------------------------------------------------------
HALLUCINATION_CHOICES_DE = [[1, "Stimme gar nicht zu"], [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"], [7, "Stimme voll zu"]]
HALLUCINATION_CHOICES_EN = [[1, "Strongly disagree"], [2, "2"], [3, "3"], [4, "4"], [5, "5"], [6, "6"], [7, "Strongly agree"]]
HALLUCINATION_CHOICES = HALLUCINATION_CHOICES_DE if LANG == 'de' else HALLUCINATION_CHOICES_EN

HALLUCINATION_FIELDS_DE = [
    ('hall_1', "Der KI-Coach bezog sich auf persönliche Details, die ich während der Sitzung nicht geteilt hatte."),
    ('hall_2', "Der KI-Coach stellte Vermutungen über mich dar, als wären es Fakten."),
    ('hall_3', "Der KI-Coach brachte Informationen über meine Situation ein, die nicht von mir stammten."),
    ('hall_4', "Der KI-Coach schien sich an Details zu erinnern oder zu verwenden, die eigentlich nicht Teil unseres Gesprächs waren."),
]
HALLUCINATION_FIELDS_EN = [
    ('hall_1', "The AI coach referred to personal details that I had not shared during the session."),
    ('hall_2', "The AI coach presented guesses about me as if they were facts."),
    ('hall_3', "The AI coach introduced information about my situation that did not come from me."),
    ('hall_4', "The AI coach seemed to remember or use details that were not actually part of our conversation."),
]
HALLUCINATION_FIELDS = HALLUCINATION_FIELDS_DE if LANG == 'de' else HALLUCINATION_FIELDS_EN

OPEN_FEEDBACK_LABEL_DE = "Möchten Sie uns noch etwas über Ihre Erfahrung mit dem KI-Coach mitteilen?"
OPEN_FEEDBACK_LABEL_EN = "Is there anything else you'd like to share about your experience with the AI coach?"
OPEN_FEEDBACK_LABEL = OPEN_FEEDBACK_LABEL_DE if LANG == 'de' else OPEN_FEEDBACK_LABEL_EN


class Constants(BaseConstants):
    name_in_url = 'Evaluation'
    players_per_group = None
    num_rounds = 1

    wai_goal_labels = dict(WAI_GOAL_FIELDS)
    wai_task_labels = dict(WAI_TASK_FIELDS)
    wai_bond_labels = dict(WAI_BOND_FIELDS)
    personalization_labels = dict(PERSONALIZATION_FIELDS)
    hallucination_labels = dict(HALLUCINATION_FIELDS)

    wai_form_fields = (
        [name for name, _ in WAI_GOAL_FIELDS]
        + [name for name, _ in WAI_TASK_FIELDS]
        + [name for name, _ in WAI_BOND_FIELDS]
    )
    ueq_form_fields = (
        [name for name, _, _ in UEQ_BEHAVIOR_FIELDS]
        + [name for name, _, _ in UEQ_QUALITY_FIELDS]
        + [name for name, _, _ in UEQ_USEFUL_FIELDS]
    )
    additional_form_fields = (
        [name for name, _ in PERSONALIZATION_FIELDS]
        + [name for name, _ in HALLUCINATION_FIELDS]
        + ['open_feedback_1']
    )

    # Preserves questionnaire dimension/item order for exports.
    form_fields = wai_form_fields + ueq_form_fields + additional_form_fields


class Subsession(BaseSubsession):
    pass


def creating_session(subsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    timestamp_evaluate_questionnaire = models.FloatField(initial=0)

    # --- WAI-SR — Goal ---
    wai_goal_1 = models.IntegerField(choices=WAI_CHOICES, label=Constants.wai_goal_labels['wai_goal_1'], widget=widgets.RadioSelect)
    wai_goal_2 = models.IntegerField(choices=WAI_CHOICES, label=Constants.wai_goal_labels['wai_goal_2'], widget=widgets.RadioSelect)
    wai_goal_3 = models.IntegerField(choices=WAI_CHOICES, label=Constants.wai_goal_labels['wai_goal_3'], widget=widgets.RadioSelect)

    # --- WAI-SR — Task ---
    wai_task_1 = models.IntegerField(choices=WAI_CHOICES, label=Constants.wai_task_labels['wai_task_1'], widget=widgets.RadioSelect)
    wai_task_2 = models.IntegerField(choices=WAI_CHOICES, label=Constants.wai_task_labels['wai_task_2'], widget=widgets.RadioSelect)
    wai_task_3 = models.IntegerField(choices=WAI_CHOICES, label=Constants.wai_task_labels['wai_task_3'], widget=widgets.RadioSelect)

    # --- WAI-SR — Bond / Interaction Quality ---
    wai_bond_1 = models.IntegerField(choices=WAI_CHOICES, label=Constants.wai_bond_labels['wai_bond_1'], widget=widgets.RadioSelect)
    wai_bond_2 = models.IntegerField(choices=WAI_CHOICES, label=Constants.wai_bond_labels['wai_bond_2'], widget=widgets.RadioSelect)
    wai_bond_3 = models.IntegerField(choices=WAI_CHOICES, label=Constants.wai_bond_labels['wai_bond_3'], widget=widgets.RadioSelect)

    # --- UEQ+ — Response behaviour (semantic differential) ---
    ueq_behavior_1 = models.IntegerField(choices=SEMANTIC_DIFFERENTIAL_SCALE, label="künstlich – natürlich", widget=widgets.RadioSelect)
    ueq_behavior_2 = models.IntegerField(choices=SEMANTIC_DIFFERENTIAL_SCALE, label="unangenehm – angenehm", widget=widgets.RadioSelect)
    ueq_behavior_3 = models.IntegerField(choices=SEMANTIC_DIFFERENTIAL_SCALE, label="unsympathisch – sympathisch", widget=widgets.RadioSelect)
    ueq_behavior_4 = models.IntegerField(choices=SEMANTIC_DIFFERENTIAL_SCALE, label="langweilig – unterhaltsam", widget=widgets.RadioSelect)

    # --- UEQ+ — Response quality (semantic differential) ---
    ueq_quality_1 = models.IntegerField(choices=SEMANTIC_DIFFERENTIAL_SCALE, label="unpassend – passend", widget=widgets.RadioSelect)
    ueq_quality_2 = models.IntegerField(choices=SEMANTIC_DIFFERENTIAL_SCALE, label="nutzlos – nützlich", widget=widgets.RadioSelect)
    ueq_quality_3 = models.IntegerField(choices=SEMANTIC_DIFFERENTIAL_SCALE, label="nicht hilfreich – hilfreich", widget=widgets.RadioSelect)
    ueq_quality_4 = models.IntegerField(choices=SEMANTIC_DIFFERENTIAL_SCALE, label="unintelligent – intelligent", widget=widgets.RadioSelect)

    # --- UEQ+ — Usefulness (semantic differential) ---
    ueq_useful_1 = models.IntegerField(choices=SEMANTIC_DIFFERENTIAL_SCALE, label="nutzlos – nützlich", widget=widgets.RadioSelect)
    ueq_useful_2 = models.IntegerField(choices=SEMANTIC_DIFFERENTIAL_SCALE, label="nicht lohnend – lohnend", widget=widgets.RadioSelect)
    ueq_useful_3 = models.IntegerField(choices=SEMANTIC_DIFFERENTIAL_SCALE, label="nicht hilfreich – hilfreich", widget=widgets.RadioSelect)
    ueq_useful_4 = models.IntegerField(choices=SEMANTIC_DIFFERENTIAL_SCALE, label="nicht vorteilhaft – vorteilhaft", widget=widgets.RadioSelect)

    # --- Personalization (manipulation check) ---
    pers_1 = models.IntegerField(choices=PERSONALIZATION_CHOICES, label=Constants.personalization_labels['pers_1'], widget=widgets.RadioSelect)
    pers_2 = models.IntegerField(choices=PERSONALIZATION_CHOICES, label=Constants.personalization_labels['pers_2'], widget=widgets.RadioSelect)
    # REVERSE-SCORED item — raw 1-7 stored as answered; use reverse_score() (8 - raw) at analysis time.
    pers_3 = models.IntegerField(choices=PERSONALIZATION_CHOICES, label=Constants.personalization_labels['pers_3'], widget=widgets.RadioSelect)

    # --- Perceived AI Hallucination ---
    hall_1 = models.IntegerField(choices=HALLUCINATION_CHOICES, label=Constants.hallucination_labels['hall_1'], widget=widgets.RadioSelect)
    hall_2 = models.IntegerField(choices=HALLUCINATION_CHOICES, label=Constants.hallucination_labels['hall_2'], widget=widgets.RadioSelect)
    hall_3 = models.IntegerField(choices=HALLUCINATION_CHOICES, label=Constants.hallucination_labels['hall_3'], widget=widgets.RadioSelect)
    hall_4 = models.IntegerField(choices=HALLUCINATION_CHOICES, label=Constants.hallucination_labels['hall_4'], widget=widgets.RadioSelect)

    # --- Open Feedback (optional, free text) ---
    open_feedback_1 = models.LongStringField(label=OPEN_FEEDBACK_LABEL, blank=True)

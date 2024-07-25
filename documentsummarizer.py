API_BASE_URL='http://10.195.176.70:8000'
API_URL = API_BASE_URL +'/apiportal/' 
LOG_API_URL=API_BASE_URL +'/logresponse/'

###############################################################################
# Import required libraries
###############################################################################
import base64
import dash
import dash_bootstrap_components as dbc
import datetime as dt
import functools
import glob
import json
import math
import os
import pathlib
import random
import requests
import shutil
import time
import traceback
import urllib.request

from dash import ALL, ClientsideFunction, dcc, html, Input, MATCH, Output, State
from flask import Flask, request
from pytz import timezone


###############################################################################
# Configurations; configure Dash to recognize the URL of the container
###############################################################################
#RUN_ON_LOCAL = 1  # True if running on local computer, False if running on Domino
APP_HEADER = 'Ask PDF'
APP_PATH = str(pathlib.Path(__file__).parent.resolve())
APP_URL = '/'
#DOMINO_PROJECT_OWNER = os.environ.get('DOMINO_PROJECT_OWNER')
#DOMINO_PROJECT_NAME = os.environ.get('DOMINO_PROJECT_NAME')
#DOMINO_RUN_ID = os.environ.get('DOMINO_RUN_ID')
#if DOMINO_PROJECT_OWNER is not None and DOMINO_PROJECT_NAME is not None and DOMINO_RUN_ID is not None:
 #   RUN_ON_LOCAL = 0
#if RUN_ON_LOCAL:
docsapp = dash.Dash(__name__, requests_pathname_prefix='/documentsummarizer/',meta_tags=[
                    {'name': 'viewport', 'content': 'width = device-width, initial-scale = 1'}], external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP, dbc.icons.FONT_AWESOME])
# else:
#     import upload_functions as uf
#     from domino import Domino
#     APP_URL = '/' + DOMINO_PROJECT_OWNER + '/' + DOMINO_PROJECT_NAME + '/r/notebookSession/' + DOMINO_RUN_ID + '/'
#     app = dash.Dash(__name__, routes_pathname_prefix='/', requests_pathname_prefix=APP_URL,
#                     title=APP_HEADER, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP, dbc.icons.FONT_AWESOME])
#     domino = Domino(DOMINO_PROJECT_OWNER + '/' + DOMINO_PROJECT_NAME)
docsapp.title = APP_HEADER
docsapp._favicon = ('nyl.png')
server = docsapp.server
docsapp.config.suppress_callback_exceptions = True


###############################################################################
# Declare constant/global/control variables
###############################################################################
FILES_ON_THE_FLY = 1

TASK_DROPDOWN_ID_TO_TEXT = {
    'summarization-mode': 'Summarization',
    'qna-mode': 'Q&A',
}

UPLOADED_FILES_SUBMITTED_DIRECTORY_FOLDER_NAME = 'uploaded_files_submitted_temp'

UPLOADED_FILES_SUBMITTED_DIRECTORY = pathlib.Path(__file__).joinpath(
    '../assets/{}'.format(UPLOADED_FILES_SUBMITTED_DIRECTORY_FOLDER_NAME)).resolve()

UPLOADED_FILES_TEMP_DIRECTORY_FOLDER_NAME = 'uploaded_files_temp'

UPLOADED_FILES_TEMP_DIRECTORY = pathlib.Path(__file__).joinpath(
    '../assets/{}'.format(UPLOADED_FILES_TEMP_DIRECTORY_FOLDER_NAME)).resolve()

UPLOAD_FILE_SIZE_LIMIT_BYTES = 20000000

UPLOAD_FILE_SIZE_LIMIT_MB = UPLOAD_FILE_SIZE_LIMIT_BYTES / 1000000

UPLOAD_FILE_SIZE_LIMIT_MB_OFFSET = 4.5

UPLOAD_FILE_NAME_LENGTH_LIMIT = 800 # Very long file name/path may cause an issue saving/loading the file

LOG_FILES_DIRECTORY_FOLDER_NAME = 'log_files'

LOG_FILES_UPLOADED_FILES_SUBMITTED_DIRECTORY_FOLDER_NAME = '{}/uploaded_files_submitted'.format(LOG_FILES_DIRECTORY_FOLDER_NAME)

CHATBOT_TEXT_BOX_STYLE_DEFAULT = {
    'max-width': '75%',
    'width': 'max-content',
    'padding': '2px 2px',
    'border-radius': 8,
    'margin-bottom': 20,
    'whiteSpace': 'pre-wrap',
    'border': 0,
    'box-shadow': 'rgba(0, 0, 0, 0.1) 0px 10px 15px -3px, rgba(0, 0, 0, 0.05) 0px 4px 6px -2px',
}

FILE_PROCESSING_TIME_MAX = 80

FILE_PROCESSING_TIME_MIN = 40

FILE_PROCESSING_SECONDS_PER_BYTE = 0.0000113 # Just an estimate, not accurate

USER_GUIDE_ACCORDION = html.Div(
    dbc.Accordion(
        [
            dbc.AccordionItem(
                [
                    html.Li('Summarization: Summarize the text content in a document. No user-customized question is allowed.'),
                    html.Li('Q&A: Enter your question related to a document and interact with an AI assistant to get answers.'),
                ],
                title='What\'s the difference between the two tasks?',
                className='border-0',
            ),
            dbc.AccordionItem(
                [
                    html.Li('The file size limit is 10 MB. Larger files will be automatically rejected.'),
                    html.Li('Ensure the file is in PDF format.'),
                    html.Li('Processing is based on raw text in the PDF. Text in images is ignored but may be supported in future versions.'),
                    html.Li('You can upload only one file. Multiple file uploads may be supported in future versions.'),
                    html.Li('All submitted files and questions will be logged but will NOT be shared outside the company\'s network.'),
                ],
                title='What do I need to know about uploading a file?',
                className='border-0',
            ),
            dbc.AccordionItem(
                [
                    html.Li('You can review your uploaded file in the Document Preview panel.'),
                ],
                title='What does the Document Preview panel do?',
                className='border-0',
            ),
            dbc.AccordionItem(
                [
                    html.Li('If you are in the Summarization mode, click "Run Summarizer!" and view your answer in the Results panel.'),
                    html.Li('If you are in the Q&A mode, type your question and press Enter or click "Submit".'),
                    html.Li('You will receive a time estimate while waiting for the answer, but please note it is just an estimate. Do not refresh the app during this time. Response time is typically < 2 minutes, depending on file size and question complexity.'),
                    html.Li('If the wait time exceeds expectations, you may reload the page and try again.'),
                    html.Li('To stop the typing effect, simply click on the text to see the full response right away.'),
                ],
                title='How do I run the model to get an answer?',
                className='border-0',
            ),
            dbc.AccordionItem(
                [
                    html.Li('Click "Copy" to copy the answer to the clipboard.'),
                    html.Li('Use the thumbs-up or thumbs-down button to rate the answer. Your feedback will be logged and valuable for future improvements.'),
                    html.Li(
                        [
                            'For detailed feedback, email ',
                            html.A(
                                'NYLIM_AI@newyorklife.com',
                                href='mailto:NYLIM_AI@newyorklife.com?subject=Web App Inquiry: {}'.format(APP_HEADER),
                                title='Contact Us',
                                target='_blank',
                                style={
                                    'textDecoration': 'none',
                                    'color': 'inherit',
                                },
                            ),
                            '. Your ideas and inputs are appreciated!',
                        ]
                    ),
                ],
                title='What else can I do once I receive a response from the model?',
                className='border-0',
            ),
            dbc.AccordionItem(
                [
                    html.Li(
                        [
                            'We utilize the ',
                            html.A(
                                'Anthropic\'s Claude model on Amazon Bedrock',
                                href='https://aws.amazon.com/bedrock/claude/',
                                title='Anthropic\'s Claude on Amazon Bedrock',
                                target='_blank',
                                style={
                                    'textDecoration': 'none',
                                    'color': 'inherit',
                                },
                            ),
                            '.',
                        ]
                    ),
                ],
                title='What technology does this tool use?',
                className='border-0',
            ),
        ],
        start_collapsed=True,
    )
)

API_MOCK_RESPONSES_SUMMARIZER = [ # Some mock responses to use when test on local without access to the API
    {
        'elapsed': 33.7,
        'user_input': 'summary',
        'summary': 
'''Here is a summary of the key financial information in the document:

- The document is the Beige Book from the Federal Reserve, summarizing economic conditions across all 12 Federal Reserve districts as of November 29, 2023.

- On balance, economic activity has slowed modestly since the previous Beige Book report. Four districts reported modest growth, two were flat to slightly down, and six saw slight declines.

- Retail sales remained mixed, with discretionary and durable goods spending declining as consumers became more price sensitive. 

- Business loan demand decreased slightly, particularly for real estate loans. Consumer credit demand remained fairly healthy.  

- Commercial real estate activity continued to slow, especially in the office segment. Residential sales and inventories also declined.

- Hiring activity eased across most districts and wage pressures moderated. However, some wage pressures persisted for high-demand roles.

- Price increases have largely moderated but prices remain elevated. Freight and shipping costs have decreased for many contacts.

- Input costs like steel and lumber have stabilized or declined, but utilities and insurance costs rose notably.

- The economic outlook for the next 6-12 months has diminished over the reporting period amid heightened uncertainty.\n\n(This is not a genuine answer; it is a paragraph created by the mock API. The actual API will be available shortly.)''',
        'tokens': 24786,
        'exception': None
    },
    {
        'elapsed': 59.1,
        'user_input': 'summary',
        'summary':
'''Here is a summary of the key points from the document:

Overview
- Chevron's 2020 Corporate Sustainability Report covers the company's approach to environmental, social and governance (ESG) issues
- Focuses on 3 pillars: protecting the environment, empowering people, getting results the right way

Environment
- Set new 2028 targets to reduce carbon intensity in upstream oil and gas production by 40% and 26% respectively from 2016 levels
- Committed to spend $2 billion through 2028 on carbon reduction projects and $750 million on renewable energy and carbon offsets 
- Joined initiatives like the World Bank's Zero Routine Flaring by 2030 and the WBCSD's Value Chain Carbon Transparency Pathfinder

Social
- Donated over $29 million to support local communities specifically for COVID-19 response
- Launched new Global Women's Leadership Development Program to increase number of women in senior roles
- Increased investment to $15 million to address racial equity and strengthen the black leadership pipeline

Governance
- Published first Climate Lobbying Report in 2020 to increase transparency on climate policy engagement
- 90%+ employees completed biennial business conduct and ethics code training
- Updated processes to regularly capture human rights and social risks across business units

Performance Data 
- Reduced upstream oil and gas GHG intensity by 40% and 26% respectively from 2016, exceeding 2023 targets
- Experienced no workforce fatalities and reduced serious injuries
- 25% of global workforce are women, 40% of Board directors are women/minorities\n\n(This is not a genuine answer; it is a paragraph created by the mock API. The actual API will be available shortly.)''',
        'tokens': 48048,
        'exception': None
    },
    {
        'exception': 'Testing exception in the summarization mode.\n\n(This is not a genuine answer; it is a paragraph created by the mock API. The actual API will be available shortly.)',
    }
]

API_MOCK_RESPONSES_CHATBOT = [
    {
        'elapsed': 25.4,
        'user_input': 'What\'s the current labor market?',
        'summary': 'The report indicates that demand for labor continued to ease, as most Districts reported flat to modest increases in overall employment. The majority of Districts reported that more applicants were available, and several noted that retention improved as well.\n\n(This is not a genuine answer; it is a paragraph created by the mock API. The actual API will be available shortly.)',
        'tokens': 24595,
        'exception': None,
        'new_question': None,
        'chat_memory': None,
    },
    {
        'elapsed': 26.0,
        'user_input': 'Is any sign the inflation stop?',
        'summary': 'Unfortunately, there is no clear sign in the document that inflation has stopped. The document indicates that price increases have largely moderated across Districts, though prices remain elevated. It also states that most Districts expect moderate price increases to continue into next year. So while inflationary pressures appear to be easing, the document does not suggest that inflation has fully stopped.\n\n(This is not a genuine answer; it is a paragraph created by the mock API. The actual API will be available shortly.)',
        'tokens': 24623,
        'exception': None,
        'new_question': None,
        'chat_memory': None,
    },
    {
        'elapsed': 49.5,
        'user_input': 'What\'s the corporate name?',
        'summary':
'''The corporate name is Chevron Corporation. This is indicated in the document in several places, such as:
"This report of Chevron Corporation contains forward-looking statements..."
"Terms of Engagement
Lloyd’s Register Quality Assurance, Inc. (LR) was commissioned by Chevron U.S.A. Inc. on behalf of Chevron Corporation (Chevron) to provide independent assurance..."
So the corporate name is Chevron Corporation.\n\n(This is not a genuine answer; it is a paragraph created by the mock API. The actual API will be available shortly.)''',
        'tokens': 47842,
        'exception': None,
        'new_question': None,
        'chat_memory': None
    },
    {
        'elapsed': 60.1,
        'user_input': 'Provide a concise, coherent, and independent summary of the document. The summary should have 5-7 sentences statement about the whole report in the begining, then following with 3 separate sections for enviorment, social, and governance. For each section, please use bullet points for summarization, and the summary should provide the following key information: (1) new goals, including the budget if there\'s any associated with any goal (2) potential risk (3) strategy',
        'summary':
'''Here is a concise summary of the key information in Chevron's 2020 Corporate Sustainability Report:
Chevron's sustainability report details the company's environmental, social, and governance (ESG) priorities and performance. Chevron aims to deliver affordable, reliable, and ever-cleaner energy while empowering people and getting results the right way.
Environment
- Set new 2028 emissions intensity reduction targets for upstream production, including 40% reduction for oil, 26% for gas, 53% for methane, and eliminating routine flaring
- Allocated $2 billion budget through 2028 on carbon reduction projects to meet targets
- Key risks include evolving climate policies and meeting aggressive emissions reduction goals
- Strategy focuses on increasing renewables and offsets, lowering carbon intensity, and investing in low-carbon technologies
Social
- Goals on diversity and inclusion, including new racial equity initiatives with $15 million budget
- Risks related to health and safety, especially with COVID-19 pandemic disrupting operations
- Strategy aims to build an inclusive culture, invest in communities, and empower people globally
Governance
- Emphasizes governance policies, Board oversight of ESG issues, and ethical business conduct
- Risks associated with regulatory compliance and transparency on lobbying activities
- Strategy focuses on stakeholder engagement, issues management, and aligning executive compensation to sustainability metrics
The report details Chevron's sustainability efforts across its operations, seeking to both mitigate ESG risks and leverage related opportunities. Key focus areas include reducing emissions, advancing diversity and inclusion, and maintaining strong governance.\n\n(This is not a genuine answer; it is a paragraph created by the mock API. The actual API will be available shortly.)''',
        'tokens': 48163,
        'exception': None,
        'new_question': None,
        'chat_memory': None
    },
    {
        'exception': 'Testing exception in the chatbot mode.\n\n(This is not a genuine answer; it is a paragraph created by the mock API. The actual API will be available shortly.)',
    }
]

API_EXCEPTION_MESSAGE_SHOW_TO_USERS = 'Sorry, there seems to be an issue with your request. Please try again later. We apologize for any inconvenience caused.'


###############################################################################
# Create the top navigation bar
###############################################################################
NAV_BAR = dbc.Navbar(
    children=[
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        [
                            html.Div(
                                dbc.NavbarBrand(
                                    [
                                        APP_HEADER,
                                        dbc.Badge(
                                            'Beta',
                                            color='light',
                                            text_color='dark',
                                            className='ms-3 py-1 px-2',
                                            style={
                                                'font-size': 'max(0.95vw, 10px)',
                                                'letter-spacing': 'normal',
                                                'font-weight': '450',
                                            },
                                        ),
                                    ],
                                    className='',
                                ),
                                className='ms-4 py-2 fade-in',
                            ),
                        ],
                        className='d-flex',
                    ),
                ),
                dbc.Col(
                    html.Div(
                        [
                            html.A(
                                html.Img(
                                    src='assets/refresh.png',
                                    style={
                                        'height': '1.9rem',
                                    },
                                ),
                                title='Refresh',
                                className='nav-bar-button me-4 fade-in',
                                style={
                                    'textDecoration': 'none',
                                    'cursor': 'pointer',
                                },
                                href=APP_URL,
                            ),
                            html.A(
                                html.Img(
                                    src='assets/mail.png',
                                    style={
                                        'height': '1.9rem',
                                    },
                                ),
                                title='Email Us',
                                className='nav-bar-button fade-in',
                                style={
                                    'textDecoration': 'none',
                                    'cursor': 'pointer',
                                },
                                href='mailto:NYLIM_AI@newyorklife.com?subject=Web App Inquiry: {}'.format(APP_HEADER),
                                target='_blank',
                            ),
                            html.A(
                                html.Img(
                                    src='assets/question.png',
                                    style={
                                        'height': '1.9rem',
                                    },
                                ),
                                id='open-user-guide-modal-button',
                                title='FAQs',
                                className='nav-bar-button ms-4 fade-in',
                                style={
                                    'textDecoration': 'none',
                                    'cursor': 'pointer',
                                },
                            ),
                        ],
                        className='d-none d-sm-block py-2',
                    ),
                    style={
                        'text-align': 'right',
                    },
                ),
                dbc.Modal(
                    [
                        dbc.ModalHeader(
                            dbc.ModalTitle(
                                'Quick Start Guide: {}'.format(APP_HEADER),
                            ),
                        ),
                        dbc.ModalBody(
                            USER_GUIDE_ACCORDION,
                        ),
                        dbc.ModalFooter(
                            [
                                ' Last updated on April 8, 2024.',
                            ],
                        ),
                    ],
                    id='user-guide-modal',
                    size='xl',
                    is_open=False,
                ),
            ],
            justify='start',
            className='mx-1 d-flex',
            style={
                'width': '100%',
            }
        ),
    ],
    color='dark',
    dark=True,
    sticky='top',
)


###############################################################################
# Create directories for uploaded files and submitted files
###############################################################################
if not os.path.exists(UPLOADED_FILES_SUBMITTED_DIRECTORY):
    os.makedirs(UPLOADED_FILES_SUBMITTED_DIRECTORY)

if not os.path.exists(UPLOADED_FILES_TEMP_DIRECTORY):
    os.makedirs(UPLOADED_FILES_TEMP_DIRECTORY)


###############################################################################
# Delete files and folders in the file upload and file submit directories
###############################################################################
def delete_files_in_repo(file_name='*', directories=[UPLOADED_FILES_SUBMITTED_DIRECTORY], file_names_to_keep=[]):
    for directory in directories:
        file_paths = glob.glob('{}/{}'.format(directory, file_name))
        for file_path in file_paths:
            if os.path.basename(file_path) in file_names_to_keep:
                continue
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)


###############################################################################
# Empty the directories for submitted files
###############################################################################
delete_files_in_repo()


###############################################################################
# Define the task dropdown list
###############################################################################
TASK_DROPDOWN_INSTRUCTION = [
    dbc.DropdownMenuItem(
        'What task do you need assistance with?',
        header=True
    )
]

TASK_DROPDOWN_ITEM = [
    dbc.DropdownMenuItem(
        TASK_DROPDOWN_ID_TO_TEXT[task_dropdown_id],
        id=task_dropdown_id
    ) for task_dropdown_id in TASK_DROPDOWN_ID_TO_TEXT
]

TASK_DROPDOWN = dbc.DropdownMenu(
    TASK_DROPDOWN_INSTRUCTION + TASK_DROPDOWN_ITEM,
    id='task-dropdown',
    label=list(TASK_DROPDOWN_ID_TO_TEXT.values())[0],
    color='secondary',
    className='my-1 row mx-1'
)


###############################################################################
# Build the user control panel on the left
###############################################################################
CONTROL_BAR = dbc.Card(
    dbc.CardBody(
        [
            html.P(
                [
                    'Engage in AI-powered conversations with any PDF. You can ask questions, get summaries, find information, and more.',
                ],
                className='d-none d-sm-block control-bar pt-4',
                style={
                    'font-size': 'max(1vw, 10.5px)',
                }
            ),
            html.Hr(
                className='d-none d-sm-block',
            ),
            html.Div(
                [
                    'Choose a task',
                    html.I(
                        id='task-selection-instruction-info-icon',
                        className='bi bi-info-circle-fill ms-2 info-icon',
                    ),
                 ],
                className='pb-2 control-bar',
            ),
            dbc.Tooltip(
                [
                    '• In summarization mode, the file content is automatically summarized.',
                    html.Br(),
                    '• In Q&A mode, you can customize your question and submit it to a chatbot.'
                ],
                target='task-selection-instruction-info-icon',
            ),
            TASK_DROPDOWN,
            html.Hr(className=''),
            html.P(
                [
                    'Upload a file',
                    html.I(
                        id='file-upload-instruction-info-icon',
                        className='bi bi-info-circle-fill ms-2 info-icon',
                    ),
                ],
                id='upload-pdf-instructions',
                className='control-bar',
            ),
            dbc.Tooltip(
                [
                    '• File size limit: 10 Mb',
                    html.Br(),
                    '• Accepted file type: PDF',
                    html.Br(),
                    '• Images or text embedded within images cannot be interpreted.',
                    html.Br(),
                    '• Only single file uploads are supported at this time.',
                ],
                target='file-upload-instruction-info-icon',
            ),
            html.Div(
                dcc.Upload(
                    id='single-file-upload',
                    children=html.Div(
                        [
                            'Drag and Drop or ',
                            html.A(
                                'Select a File',
                                style={
                                    'cursor': 'pointer',
                                },
                            ),
                        ],
                        id='single-file-upload-inner',
                        title='Click to choose a file',
                        className='control-bar',
                    ),
                    style={
                        'borderWidth': '2px',
                        'borderRadius': '5px',
                        'textAlign': 'center',
                        'padding-top': '19px',
                        'padding-bottom': '19px',
                        'padding-left': '4px',
                        'padding-right': '4px',
                    },
                    max_size=UPLOAD_FILE_SIZE_LIMIT_BYTES,
                    multiple=False,
                    accept='application/pdf',
                    className='mx-1',
                ),
                id='single-file-upload-wrapper',
            ),
            dbc.Spinner(
                html.Div(
                    id='file-upload-loading-component',
                ),
                fullscreen=True,
                fullscreen_class_name='file-upload-spinner-fullscreen',
            ),
            html.P(
                'You have not uploaded any file.',
                id='single-file-upload-info',
                className='mt-3 mx-1 control-bar',
            ),
            dcc.Store(
                id='single-file-upload-estimate-store',
                data=[0, 0, '', '', '', ''], # file size, processing time estimate, original file name, new file name (empty if not submitted yet), file content, timestamp id when the file is first uploaded
            ),
            html.Hr(),
            dbc.Button(
                'Run Summarizer!',
                id='submit-button',
                title='Submit a file to the Summarizer',
                color='secondary',
                disabled=True,
                style={
                    'width': '100%',
                },
            ),
            dbc.Spinner(
                html.Div(
                    id='submit-button-loading-component',
                ),
                id='submit-button-loading-component-spinner',
                fullscreen=True,
                fullscreen_class_name='spinner-fullscreen',
                show_initially=False,
            ),
            html.Div(
                html.A(
                    html.Img(
                        src='assets/nyl_inv_logo.svg',
                        className='nyl-inv-logo',
                        style={
                            'background': 'transparent',
                            'width': '100%',
                        },
                    ),
                    href='https://www.newyorklifeinvestments.com/',
                    target='_blank',
                    title='More than investing. Invested | New York Life Investments',
                    style={
                        'textDecoration': 'none',
                    },
                ),
                className='fade-in d-none d-xl-block nylim-logo-bottom',
                style={
                    'bottom': '2.75rem',
                    'position': 'absolute',
                },
            ),
        ],
        className='col-10 mx-auto control-bar pt-2',
    ),
    className='border-0 bg-transparent fade-in row',
    style={
       'height': 'calc(100vh - 2.15625rem)',
    }
)


###############################################################################
# Build the panel to display/preview docs in the middle
###############################################################################
DISPLAY_PANEL = dbc.Card(
    dbc.CardBody(
        [
            html.H5(
                [
                    'Document Preview',
                    html.I(
                        id='document-snapshot-instruction-info-icon',
                        className='bi bi-info-circle-fill ms-2 info-icon',
                    ),
                ],
                id='document-snapshot-header',
                className='card-title d-none'
            ),
            dbc.Tooltip(
                [
                    '• Review your document here before sending it to the model.',
                ],
                target='document-snapshot-instruction-info-icon',
            ),
            html.Iframe(
                id='uploaded-file-preview',
                src='',
                height='89%',
                width='100%',
                className='my-2',
            ),
        ],
        className='bg-light',
    ),
    className='border-0 bg-transparent fade-in',
    style={
       'height': 'calc(100vh - 2.15625rem)',
    }
)


###############################################################################
# Get time info
###############################################################################
def get_time_info():
    tz_eastern = timezone('US/Eastern')  # Get time info
    start_time = dt.datetime.now(tz=tz_eastern)
    transferDateTime = start_time.strftime('%Y-%m-%d %H-%M-%S-%f')
    timestamp_id = start_time.strftime('%Y%m%d%H%M%S%f')
    return tz_eastern, start_time, transferDateTime, timestamp_id


###############################################################################
# Create the chatbot copy button after the answer
###############################################################################
def create_chatbot_copy_to_clipboard_button(text_box_index, summarizer_mode='chatbot'):
    return dbc.Button(
        [
            html.I(
                id={
                    'type': '{}-copy-results-icon'.format(summarizer_mode),
                    'index': text_box_index
                },
                className='bi bi-clipboard'
            ),
            dbc.Popover(
                target={
                    'type': '{}-copy-results'.format(summarizer_mode),
                    'index': text_box_index
                },
                trigger='hover',
                id={
                    'type': '{}-copy-results-icon-popover'.format(summarizer_mode),
                    'index': text_box_index
                },
                className='d-none',
                is_open=False,
            ),
            dcc.Clipboard(
                target_id={
                    'type': '{}-text-card'.format(summarizer_mode),
                    'index': text_box_index
                },
                className='position-absolute start-0 top-0 h-100 w-100 opacity-0',
            ),
            dbc.Tooltip(
                'Copied!',
                id={
                    'type': '{}-copy-tooltip-clicked'.format(summarizer_mode),
                    'index': text_box_index
                },
                target={
                    'type': '{}-copy-results'.format(summarizer_mode),
                    'index': text_box_index
                },
                placement='top',
                is_open=False,
                trigger='click',
            ),
        ],
        id={
            'type': '{}-copy-results'.format(summarizer_mode),
            'index': text_box_index
        },
        outline=True,
        title='Copy',
        size='sm',
        color='primary',
        className='position-relative me-1 py-0',
    )


###############################################################################
# Create the chatbot good response button after the answer
###############################################################################
def create_chatbot_thumb_up_button(text_box_index, summarizer_mode='chatbot'):
    return dbc.Button(
        [
            html.I(
                id={
                    'type': '{}-good-response-icon'.format(summarizer_mode),
                    'index': text_box_index
                },
                className='bi bi-hand-thumbs-up'
            ),
            dbc.Popover(
                target={
                    'type': '{}-good-response'.format(summarizer_mode),
                    'index': text_box_index
                },
                trigger='hover',
                id={
                    'type': '{}-good-response-icon-popover'.format(summarizer_mode),
                    'index': text_box_index
                },
                className='d-none',
                is_open=False,
            ),
            dbc.Tooltip(
                'Thanks for your feedback!',
                id={
                    'type': '{}-good-response-tooltip-clicked'.format(summarizer_mode),
                    'index': text_box_index
                },
                target={
                    'type': '{}-good-response'.format(summarizer_mode),
                    'index': text_box_index
                },
                placement='top',
                is_open=False,
                trigger='click',
            ),
        ],
        id={
            'type': '{}-good-response'.format(summarizer_mode),
            'index': text_box_index
        },
        outline=True,
        title='Good Response',
        size='sm',
        color='primary',
        className='me-1 py-0',
    )


###############################################################################
# Create the chatbot bad response button after the answer
###############################################################################
def create_chatbot_thumb_down_button(text_box_index, summarizer_mode='chatbot'):
    return dbc.Button(
        [
            html.I(
                id={
                    'type': '{}-bad-response-icon'.format(summarizer_mode),
                    'index': text_box_index
                },
                className='bi bi-hand-thumbs-down'
            ),
            dbc.Popover(
                target={
                    'type': '{}-bad-response'.format(summarizer_mode),
                    'index': text_box_index
                },
                trigger='hover',
                id={
                    'type': '{}-bad-response-icon-popover'.format(summarizer_mode),
                    'index': text_box_index
                },
                className='d-none',
                is_open=False,
            ),
            dbc.Tooltip(
                'Thanks for your feedback!',
                id={
                    'type': '{}-bad-response-tooltip-clicked'.format(summarizer_mode),
                    'index': text_box_index
                },
                target={
                    'type': '{}-bad-response'.format(summarizer_mode),
                    'index': text_box_index
                },
                placement='top',
                is_open=False,
                trigger='click',
            ),
        ],
        id={
            'type': '{}-bad-response'.format(summarizer_mode),
            'index': text_box_index
        },
        outline=True,
        title='Bad Response',
        size='sm',
        color='primary',
        className='me-1 py-0',
    )


###############################################################################
# Copy, good response, and bad response buttons for the summarizer
###############################################################################
ANSWER_RATING = dbc.ButtonGroup(
    [
        dbc.Button(
            [
                html.I(
                    id='copy-results-icon',
                    className='bi bi-clipboard',
                ),
                dbc.Popover(
                    target='copy-results',
                    trigger='hover',
                    id='copy-results-icon-popover',
                    className='d-none',
                    is_open=False,
                ),
                dcc.Clipboard(
                    id='results-display-clipboard',
                    target_id='results-display',
                    className='position-absolute start-0 top-0 h-100 w-100 opacity-0',
                ),
                dbc.Tooltip(
                    'Copied!',
                    id='copy-results-tooltip-clicked',
                    target='copy-results',
                    placement='top',
                    is_open=False,
                    trigger=None,
                ),
            ],
            id='copy-results',
            outline=True,
            color='primary',
            title='Copy',
            size='sm',
            className='me-1',
        ),
        dbc.Button(
            [
                html.I(
                    id='good-response-icon',
                    className='bi bi-hand-thumbs-up'
                ),
                dbc.Popover(
                    target='good-response',
                    trigger='hover',
                    id='good-response-icon-popover',
                    className='d-none',
                    is_open=False,
                ),
                dbc.Tooltip(
                    'Thanks for your feedback!',
                    id='good-response-tooltip-clicked',
                    target='good-response',
                    placement='top',
                    is_open=False,
                    trigger=None,
                ),
            ],
            id='good-response',
            outline=True,
            color='primary',
            title='Good Response',
            size='sm',
            className='me-1',
        ),
        dbc.Button(
            [
                html.I(
                    id='bad-response-icon',
                    className='bi bi-hand-thumbs-down'
                ),
                dbc.Popover(
                    target='bad-response',
                    trigger='hover',
                    id='bad-response-icon-popover',
                    className='d-none',
                    is_open=False,
                ),
                dbc.Tooltip(
                    'Thanks for your feedback!',
                    id='bad-response-tooltip-clicked',
                    target='bad-response',
                    placement='top',
                    is_open=False,
                    trigger=None,
                ),
            ],
            id='bad-response',
            outline=True,
            color='primary',
            title='Bad Response',
            size='sm',
            className='me-1',
        ),
    ],
    id='answer-rating-button-group',
    className='border-0 bg-transparent border-0 mb-3 fade-in pt-0 pb-4',
    style={
        'display': 'none',
    }
)


###############################################################################
# Create a user text box
###############################################################################
def create_user_text_box(text_box_index, text_box_content, domino_username, filename_timestamp_readable, original_file_name, enable_chat_history):
    text_box_style = CHATBOT_TEXT_BOX_STYLE_DEFAULT.copy()
    text_box_style['margin-left'] = 'auto'
    text_box_style['margin-right'] = 10
    new_session_divider_display = ''
    if enable_chat_history:
        new_session_divider_display = 'none'
    new_session_divider = html.Div(
        [
            html.I(
                className='bi bi-upload me-2',
                style={
                    'color': 'gray',
                    'font-size': 'max(0.8vw, 9.5px)',
                },
            ),
            'File uploaded: {}'.format(original_file_name),
        ],
        className='text-center pb-3 pt-3 fade-in text-muted',
        style={
            'color': 'gray',
            'font-size': 'max(0.8vw, 9.5px)',
            'display': new_session_divider_display,
        },
    )
    return html.Div(
        [
            new_session_divider,
            dbc.Card(
                [
                    html.Div(
                        [
                            text_box_content,
                        ],
                        title='Asked by user {} on {} for {}'.format(domino_username, filename_timestamp_readable, original_file_name),
                        id={
                            'type': 'chatbot-user-text-card',
                            'index': text_box_index
                        },
                        style={
                            'color': 'white',
                            'font-size': 'max(0.9vw, 11px)',
                        },
                    ),
                ],
                className='fade-in',
                style=text_box_style,
                body=True,
                color='secondary',
                inverse=True,
            )
        ]
    )


###############################################################################
# Create a bot/AI text box
###############################################################################
def create_ai_text_box(text_box_index, text_box_content, original_file_name, new_file_name):
    filename_timestamp_readable = dt.datetime.now(tz=timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S')
    text_box_style = CHATBOT_TEXT_BOX_STYLE_DEFAULT.copy()
    text_box_style['margin-left'] = 0
    text_box_style['margin-right'] = 'auto'
    text_box_style['width'] = '99%'
    thumbnail = html.Img(
        id={
            'type': 'chatbot-text-card-profile',
            'index': text_box_index
        },
        src='assets/bot_blue.png',
        style={
            'height': 36,
            'margin-right': 5,
            'float': 'left',
        },
    )
    text_box = dbc.Card(
        [
            html.Div(
                [
                    text_box_content,
                ],
                title='Answered on {} for {}'.format(filename_timestamp_readable, original_file_name),
                id={
                    'type': 'chatbot-text-card',
                    'index': text_box_index
                },
                style = {
                    'display': 'none',
                    'font-size': 'max(0.9vw, 11px)',
                }
            ),
            html.Hr(),
            html.Div(
                [
                    create_chatbot_copy_to_clipboard_button(
                        text_box_index),
                    create_chatbot_thumb_up_button(text_box_index),
                    create_chatbot_thumb_down_button(text_box_index),
                ],
                id={
                    'type': 'chatbot-text-card-buttons',
                    'index': text_box_index,
                },
                style={
                    'visibility': 'hidden',
                    'height': '5px!important',
                },
            ),
            dcc.Store(
                id={
                    'type': 'chatbot-text-card-file-name-store',
                    'index': text_box_index,
                },
                data=[
                    original_file_name,
                    new_file_name
                ],
            ),
        ],
        className='fade-in',
        style=text_box_style,
        body=True,
        color='light',
        inverse=False,
    )
    return html.Div([thumbnail, text_box])


###############################################################################
# A decorator used to log exception and prevent the app from updating when an 
# error occurs
###############################################################################
def prevent_update_on_error(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            tz_eastern, start_time, transferDateTime, timestamp_id = get_time_info()
            traceback_info = traceback.format_exc()
            generate_exception_log(tz_eastern, start_time, transferDateTime, timestamp_id, str(traceback_info))
            raise dash.exceptions.PreventUpdate
    return wrapper


###############################################################################
# Log when the chatbot's copy results button is clicked
###############################################################################
@docsapp.callback(
    Output({'type': 'chatbot-copy-results', 'index': MATCH}, 'n_clicks'),
    Input({'type': 'chatbot-copy-results', 'index': MATCH}, 'n_clicks'),
    State({'type': 'chatbot-text-card', 'index': MATCH}, 'children'),
    State({'type': 'chatbot-user-text-card', 'index': MATCH}, 'children'),
    State({'type': 'chatbot-text-card-file-name-store', 'index': MATCH}, 'data'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def submit_chatbot_copy_response(chatbot_copy_response_n_clicks, chatbot_text_card_value, chatbot_user_text_card_value, chatbot_text_card_file_name_store_data):
    tz_eastern, start_time, transferDateTime, timestamp_id = get_time_info()

    original_filename = chatbot_text_card_file_name_store_data[0]
    new_filename = chatbot_text_card_file_name_store_data[1]

    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if 'chatbot-copy-results' in changed_id:
        generate_log(tz_eastern, start_time, transferDateTime, timestamp_id, 'chatbot', 'copied',
            '', new_filename, str(chatbot_user_text_card_value[0]), str(chatbot_text_card_value[0]))
    return dash.no_update


###############################################################################
# Log when the chatbot's good response button is clicked
###############################################################################
@docsapp.callback(
    Output({'type': 'chatbot-good-response', 'index': MATCH}, 'n_clicks'),
    Input({'type': 'chatbot-good-response', 'index': MATCH}, 'n_clicks'),
    State({'type': 'chatbot-text-card', 'index': MATCH}, 'children'),
    State({'type': 'chatbot-user-text-card', 'index': MATCH}, 'children'),
    State({'type': 'chatbot-text-card-file-name-store', 'index': MATCH}, 'data'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def submit_chatbot_good_response(chatbot_good_response_n_clicks, chatbot_text_card_value, chatbot_user_text_card_value, chatbot_text_card_file_name_store_data):
    tz_eastern, start_time, transferDateTime, timestamp_id = get_time_info()

    original_filename = chatbot_text_card_file_name_store_data[0]
    new_filename = chatbot_text_card_file_name_store_data[1]

    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if 'chatbot-good-response' in changed_id:
        generate_log(tz_eastern, start_time, transferDateTime, timestamp_id, 'chatbot', 'good-response',
            '', new_filename, str(chatbot_user_text_card_value[0]), str(chatbot_text_card_value[0]))
    return dash.no_update


###############################################################################
# Log when the chatbot's bad response button is clicked
###############################################################################
@docsapp.callback(
    Output({'type': 'chatbot-bad-response', 'index': MATCH}, 'n_clicks'),
    Input({'type': 'chatbot-bad-response', 'index': MATCH}, 'n_clicks'),
    State({'type': 'chatbot-text-card', 'index': MATCH}, 'children'),
    State({'type': 'chatbot-user-text-card', 'index': MATCH}, 'children'),
    State({'type': 'chatbot-text-card-file-name-store', 'index': MATCH}, 'data'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def submit_chatbot_bad_response(chatbot_bad_response_n_clicks, chatbot_text_card_value, chatbot_user_text_card_value, chatbot_text_card_file_name_store_data):
    tz_eastern, start_time, transferDateTime, timestamp_id = get_time_info()

    original_filename = chatbot_text_card_file_name_store_data[0]
    new_filename = chatbot_text_card_file_name_store_data[1]

    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if 'chatbot-bad-response' in changed_id:
        generate_log(tz_eastern, start_time, transferDateTime, timestamp_id, 'chatbot', 'bad-response',
            '', new_filename, str(chatbot_user_text_card_value[0]), str(chatbot_text_card_value[0]))
    return dash.no_update


###############################################################################
# Show the Copied tooltip upon clicking the summarizer's copy button
###############################################################################
@docsapp.callback(
    Output('copy-results-tooltip-clicked', 'is_open'),
    Input('copy-results', 'n_clicks'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def open_copy_tooltip_upon_click(copy_results_n_clicks):
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if 'copy-results' in changed_id:
        return True
    return dash.no_update


###############################################################################
# Hide the summarizer's Copied tooltip after it has been open for some time
###############################################################################
@docsapp.callback(
    Output('copy-results-tooltip-clicked', 'is_open', allow_duplicate=True),
    Input('copy-results-tooltip-clicked', 'is_open'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def hide_copy_tooltip_after_seconds(copy_tooltip_is_open):
    if copy_tooltip_is_open:
        time.sleep(0.5)
        return False
    return dash.no_update


###############################################################################
# Show the good response tooltip upon clicking the summarizer's thumb up button
###############################################################################
@docsapp.callback(
    Output('good-response-tooltip-clicked', 'is_open'),
    Input('good-response', 'n_clicks'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def open_good_response_tooltip_upon_click(good_response_n_clicks):
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if 'good-response' in changed_id:
        return True
    return dash.no_update


###############################################################################
# Hide the summarizer's good response tooltip after it has been open for some 
# time
###############################################################################
@docsapp.callback(
    Output('good-response-tooltip-clicked', 'is_open', allow_duplicate=True),
    Input('good-response-tooltip-clicked', 'is_open'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def hide_good_response_tooltip_after_seconds(good_response_tooltip_is_open):
    if good_response_tooltip_is_open:
        time.sleep(0.5)
        return False
    return dash.no_update


###############################################################################
# Show the bad response tooltip upon clicking the summarizer's thumb down 
# button
###############################################################################
@docsapp.callback(
    Output('bad-response-tooltip-clicked', 'is_open'),
    Input('bad-response', 'n_clicks'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def open_bad_response_tooltip_upon_click(bad_response_n_clicks):
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if 'bad-response' in changed_id:
        return True
    return dash.no_update


###############################################################################
# Hide the summarizer's bad response tooltip after it has been open for some 
# time
###############################################################################
@docsapp.callback(
    Output('bad-response-tooltip-clicked', 'is_open', allow_duplicate=True),
    Input('bad-response-tooltip-clicked', 'is_open'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def hide_bad_response_tooltip_after_seconds(bad_response_tooltip_is_open):
    if bad_response_tooltip_is_open:
        time.sleep(0.5)
        return False
    return dash.no_update


###############################################################################
# Hide the chatbot's Copied tooltip after it has been open for some time
###############################################################################
@docsapp.callback(
    Output({'type': 'chatbot-copy-tooltip-clicked', 'index': MATCH}, 'is_open', allow_duplicate=True),
    Input({'type': 'chatbot-copy-tooltip-clicked', 'index': MATCH}, 'is_open'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def hide_chatbot_copy_tooltip_after_seconds(chatbot_copy_tooltip_is_open):
    if chatbot_copy_tooltip_is_open:
        time.sleep(0.5)
        return False
    return dash.no_update


###############################################################################
# Hide the chatbot's good response tooltip after it has been open for some time
###############################################################################
@docsapp.callback(
    Output({'type': 'chatbot-good-response-tooltip-clicked', 'index': MATCH}, 'is_open', allow_duplicate=True),
    Input({'type': 'chatbot-good-response-tooltip-clicked', 'index': MATCH}, 'is_open'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def hide_chatbot_good_response_tooltip_after_seconds(chatbot_good_response_tooltip_is_open):
    if chatbot_good_response_tooltip_is_open:
        time.sleep(0.5)
        return False
    return dash.no_update


###############################################################################
# Hide the chatbot's bad response tooltip after it has been open for some time
###############################################################################
@docsapp.callback(
    Output({'type': 'chatbot-bad-response-tooltip-clicked', 'index': MATCH}, 'is_open', allow_duplicate=True),
    Input({'type': 'chatbot-bad-response-tooltip-clicked', 'index': MATCH}, 'is_open'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def hide_chatbot_bad_response_tooltip_after_seconds(chatbot_bad_response_tooltip_is_open):
    if chatbot_bad_response_tooltip_is_open:
        time.sleep(0.5)
        return False
    return dash.no_update


###############################################################################
# Build the container for the chatbot
###############################################################################
CHATBOT_CONTAINER = dbc.Container(
    id='chatbot-container',
    fluid=False,
    children=[
        html.Hr(),
        dcc.Store(
            id='store-conversation-and-file-name',
            data=[], # List of list, each list is user input text, chatbot answer text, original filename, new filename, Domino username, timestamp, enable chat history boolean
        ),
        dbc.InputGroup(
            children=[
                dbc.Textarea(
                    id='chatbot-user-input',
                    placeholder='Please upload a file first.',
                    autofocus=False,
                    disabled=True,
                    rows=1,
                    spellcheck='true',
                    style={
                        'resize': 'none',
                        'scrollbar-gutter': 'stable both-edges',
                        'border-radius': '0.375rem',
                        'box-sizing': 'content-box',
                    },
                ),
                dbc.Button(
                    'Submit',
                    id='chatbot-submit-button',
                    disabled=True,
                    color='secondary',
                    title='Submit your question to the Chatbot',
                    style={
                        'height': '100%',
                        'margin-left': '5px',
                        'border-radius': '0.375rem',
                    }
                ),
            ],
            id='chatbot-user-input-group',
            style={
                'align-items': 'flex-end',
            },
        ),
        html.P(
            'The LLM can make mistakes. Consider checking important information. Use Shift + Enter to create a new line.',
            className='text-muted px-2 pt-2 pb-3',
            style={
                'font-size': 'max(0.675vw, 8.75px)'
            }
        ),
        html.Div(
            html.Div(
                id='display-conversation',
            ),
            style={
                'overflow-y': 'auto',
                'display': 'flex',
                'height': 'calc(79.5vh - 120px)',
                'flex-direction': 'column-reverse',
            },
        ),
        dcc.Store(
            id='chatbot-submit-button-n-clicks-store',
            data=0, # Number of times the chatbot submit button is clicked upon successfully uploading a new file
        ),
        dbc.Spinner(
            html.Div(
                id='loading-component',
            ),
            id='loading-component-spinner',
            fullscreen=True,
            fullscreen_class_name='spinner-fullscreen',
        ),
    ],
    className='fade-in',
    style={
        'display': 'none',
    },
)


###############################################################################
# Build the panel to display results on the right
###############################################################################
RESULTS_PANEL = dbc.Card(
    dbc.CardBody(
        [
            html.H5(
                [
                    'Results',
                    html.I(
                        id='results-overview-instruction-info-icon',
                        className='bi bi-info-circle-fill ms-2 info-icon',
                    ),
                ],
                id='results-overview-header',
                className='card-title pb-2 d-none'
            ),
            dbc.Tooltip(
                [
                    '• The summary or chatbot response will appear here.',
                    html.Br(),
                    '• Click text to speed up typing.',
                    html.Br(),
                    '• Rate the response to help us enhance this application.'
                ],
                target='results-overview-instruction-info-icon',
            ),
            CHATBOT_CONTAINER,
            html.P(
                '', 
                id='results-display', # Show the text including the animation
                className='bg-transparent px-2 py-3 rounded fade-in',
                style={
                    'font-size': 'max(0.82vw, 10.5px)',
                    'whiteSpace': 'pre-wrap',
                    'display': 'none',
                }
            ),
            html.P(
                '', 
                id='results-display-full-text', # Store the full text but do not show
                style={
                    'display': 'none',
                }
            ),
            html.P(
                'The LLM can make mistakes. Consider checking important information.',
                id='summarizer-disclaimer',
                className='text-muted ps-2 my-2 fade-in',
                style={
                    'font-size': 'max(0.675vw, 8.75px)',
                    'display': 'none',
                }
            ),
            ANSWER_RATING,
            dcc.Store(
                id='summarizer-last-submit-store',
                data='',
            ),
        ],
        className='bg-light',
    ),
    className='border-0 bg-transparent fade-in',
    style={
       'height': 'calc(100vh - 2.15625rem)',
    },
)


###############################################################################
# Build the main content of the page under the navigation bar
###############################################################################
MAIN_PAGE_CONTENT = dbc.Row(
    [
        dbc.Col(
            CONTROL_BAR,
            className='col-3 overflow-auto control-bar-wrapper bg-white',
        ),
        dbc.Col(
            DISPLAY_PANEL,
            className='col-4 overflow-auto',
        ),
        dbc.Col(
            RESULTS_PANEL,
            id='results-panel',
            className='overflow-auto bg-light',
            style={}
        ),
    ],
    className='g-0 bg-light',
)


###############################################################################
# Create the main app layout
###############################################################################
docsapp.layout = html.Div(
    [
        NAV_BAR,
        MAIN_PAGE_CONTENT,
    ],
)


###############################################################################
# Change the task label and task options
###############################################################################
@docsapp.callback(
    Output('task-dropdown', 'label', allow_duplicate=True),
    Input('summarization-mode', 'n_clicks'),
    Input('qna-mode', 'n_clicks'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def update_task_label(*args):
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    for changed_id_candidate in list(TASK_DROPDOWN_ID_TO_TEXT.keys()):
        if changed_id_candidate in changed_id:
            changed_id = changed_id_candidate
    return TASK_DROPDOWN_ID_TO_TEXT[changed_id]


###############################################################################
# Make a copy from /mnt to Files on Domino
# Otherwise cannot see changes while the app is running
###############################################################################
# def update_from_mount(new_filename):
#     try:
#         f = open('{}/assets/{}/{}'.format(APP_PATH, UPLOADED_FILES_SUBMITTED_DIRECTORY_FOLDER_NAME, new_filename), 'rb')
#         r = domino.files_upload('/{}/{}'.format(LOG_FILES_UPLOADED_FILES_SUBMITTED_DIRECTORY_FOLDER_NAME, new_filename), f)
#         if r.status_code == 201:
#             print('Upload successful')
#         else:
#             print('Upload failed')
#     except Exception as e:
#         tz_eastern, start_time, transferDateTime, timestamp_id = get_time_info()
#         traceback_info = traceback.format_exc()
#         generate_exception_log(tz_eastern, start_time, transferDateTime, timestamp_id, str(traceback_info))
#         print(str(e))


###############################################################################
# Copy one file from the file upload directory to the submitted directory and 
# rename it
###############################################################################
def rename_and_save_uploaded_files_to_submit_dir(original_filename, new_filename, content):
    data = content.encode('utf8').split(b';base64,')[1]
    with open(os.path.join(UPLOADED_FILES_SUBMITTED_DIRECTORY, new_filename), 'wb') as fp:
        fp.write(base64.decodebytes(data))
    #if not RUN_ON_LOCAL:
       # update_from_mount(new_filename)


###############################################################################
# Show chatbot container when Q&A is selected
###############################################################################
@docsapp.callback(
    Output('results-display', 'style', allow_duplicate=True),
    Output('summarizer-disclaimer', 'style', allow_duplicate=True),
    Output('answer-rating-button-group', 'style', allow_duplicate=True),
    Output('chatbot-container', 'style'),
    Output('submit-button', 'style'),
    Input('task-dropdown', 'label'),
    State('summarizer-last-submit-store', 'data'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def hide_show_chatbot_container(task_dropdown_label, summarizer_last_submit_store_data):
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if 'task-dropdown.label' in changed_id and 'Q&A' in task_dropdown_label:
        return {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, {}, {'display': 'none'}
    elif summarizer_last_submit_store_data == '':
        return {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, {'width': '100%'}
    return {'font-size': 'max(0.82vw, 10.5px)', 'whiteSpace': 'pre-wrap'}, {'font-size': 'max(0.675vw, 8.75px)'}, {}, {'display': 'none'}, {'width': '100%'}


###############################################################################
# Disable the chatbot's submit button when no file is uploaded or no question
# is asked
###############################################################################
@docsapp.callback(
    Output('chatbot-submit-button', 'disabled'),
    Input('chatbot-user-input', 'value'),
    Input('uploaded-file-preview', 'src'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def update_chatbot_submit_button(chatbot_user_input_value, uploaded_file_preview_src):
    if chatbot_user_input_value is not None and len(chatbot_user_input_value) and uploaded_file_preview_src is not None and len(uploaded_file_preview_src) and bool(chatbot_user_input_value.strip()):
        return False
    return True

###############################################################################
# Save log files to AWS
###############################################################################
def generate_log_aws(log_data):
     headers = {'Content-Type': 'application/json'}
     try:
        #print("log data is {}".format(log_data))
        response = requests.post(LOG_API_URL, headers=headers,json={"log_data":log_data})

     except Exception as e:
        print(e)
        pass
     


###############################################################################
# Do not log original file info, and instead, log the length of each string
###############################################################################
def log_files_on_the_fly(user_input, results_paragraph, results_json_from_api, submit_type):
    if FILES_ON_THE_FLY: # instead of logging the original info, log the length only
        user_input = str(len(user_input))
        results_paragraph = str(len(results_paragraph))
        if submit_type == 'submitted' and results_json_from_api is not None and len(results_json_from_api):
            results_json_from_api = json.loads(results_json_from_api)
            if 'summary' in results_json_from_api:
                results_json_from_api['summary'] = str(len(results_json_from_api['summary']))
            if 'user_input' in results_json_from_api:
                results_json_from_api['user_input'] = str(len(results_json_from_api['user_input']))
            results_json_from_api = json.dumps(results_json_from_api)
    return user_input, results_paragraph, results_json_from_api

###############################################################################
# Generate log files
###############################################################################
def generate_log(tz_eastern, start_time, transferDateTime, timestamp_id, mode, submit_type, file_size, new_filename, user_input, results_paragraph, results_json_from_api=''):
    try:
        processing_time = dt.datetime.now(tz=tz_eastern) - start_time
        ptime = str(processing_time.seconds + processing_time.microseconds / 1000000)
        
        # user_input = user_input.replace('\n', '\\n')
        # user_input = user_input.replace('\t', '\\n')
        # user_input = user_input.encode('latin-1', 'ignore').decode('latin-1')
        # results_paragraph = results_paragraph.replace('\n', '\\n')
        # results_paragraph = results_paragraph.replace('\t', '\\n')
        # results_paragraph = results_paragraph.encode('latin-1', 'ignore').decode('latin-1')
        results_json_from_api = results_json_from_api.replace('\t', '\\n')
        results_json_from_api = results_json_from_api.encode('latin-1', 'ignore').decode('latin-1')
        
        #user_input, results_paragraph, results_json_from_api = log_files_on_the_fly(user_input, results_paragraph, results_json_from_api, submit_type)

        log_list = {
            "username": request.headers.get('domino-username'), # Domino username; None if on local
            "timestamp":timestamp_id, # YYYYMMDDHHMMSS
            "processing time": ptime, # Processing time
            "status":'Success', # Success (or Fail for exception log)
            "ai_mode":mode, # summarizer or chatbot
            "submit_type":submit_type, # submitted, copied, good-response, or bad-response
            "file size":file_size, # File size in bytes (replaced original file name as we no longer need this info)
            "new file name":new_filename, # New file name (username-timestamp including milliseconds) ending with .pdf
            "user input":user_input, # Size of prompt entered to the chatbot, empty string for summarizer
            "results":results_paragraph, # length of the answer from either the summarizer or the chatbot
            "results json from api":results_json_from_api, # More detailed results in JSON format passed back from the API; summary and user input are their length
            "Errorr message":'None' # Placeholder for error message
        }
        print(log_list)
        log_data="\n".join([f"{key}:{value}" for key,value in log_list.items()])
        generate_log_aws(log_data)
        #if not RUN_ON_LOCAL:
            #uf.dominoPut('{}/{}/{}/{}.csv'.format(DOMINO_PROJECT_OWNER, DOMINO_PROJECT_NAME, LOG_FILES_DIRECTORY_FOLDER_NAME, transferDateTime), log_list)
    except Exception as e:
        print(e)
        pass


###############################################################################
# Generate log files when exceptions occur
###############################################################################
def generate_exception_log(tz_eastern, start_time, transferDateTime, timestamp_id, traceback_info):
    try:
        if tz_eastern == '' and start_time == '' and transferDateTime == '' and timestamp_id == '':
            ptime = ''
        else:
            processing_time = dt.datetime.now(tz=tz_eastern) - start_time
            ptime = str(processing_time.seconds + processing_time.microseconds / 1000000)

        traceback_info = traceback_info.replace('\n', '\\n')
        traceback_info = traceback_info.replace('\t', '\\n')

        log_list = [
            request.headers.get('domino-username'),
            timestamp_id,
            ptime,
            'Fail',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            traceback_info # Error message
        ]
        print(log_list)
        #if not RUN_ON_LOCAL:
         #   uf.dominoPut('{}/{}/{}/{}.csv'.format(DOMINO_PROJECT_OWNER, DOMINO_PROJECT_NAME, LOG_FILES_DIRECTORY_FOLDER_NAME, transferDateTime), log_list)  # path subject to change
    except Exception as e:
        print(e)
        pass


###############################################################################
# Get answers from the real API from AWS
# app_mode: a string, either "Document Summary" or "ChatPDF"
# file_id: a string, unique for each uploaded file (E.g., If a user uploads a file and then submits multiple questions to the chatbot, file_id will remain unchanged for subsequent submissions)
# original_filename: a string (NOT a unique identifier as different users may upload files with the same name)
# enable_chat_history: an integer, 0 or 1; 0 when submitting a newly uploaded file for the first time to the chatbot; useful only when app_mode is “ChatPDF”
# binary_file_content: a binary string, "" if enable_chat_history is 1
# user_input: a string, "" if app_mode is "Document Summary"
###############################################################################
def get_answers_from_app_api_portal(app_mode, file_id, original_filename, enable_chat_history, binary_file_content, user_input):
    #if RUN_ON_LOCAL: # For calling the real API
    headers = {'Content-Type': 'application/json'}
    data = json.dumps( # Send the Base64 encoded file content inside a JSON payload
        {
            'app_mode': app_mode,
            'file_id': file_id,
            'original_filename': original_filename,
            'enable_chat_history': enable_chat_history,
            'file_content': binary_file_content,
            'user_input': user_input,
        }
    )
    try:
        response = requests.post(API_URL, headers=headers, data=data)
    except Exception as e:
        return '{} (Connectivity Issue)'.format(API_EXCEPTION_MESSAGE_SHOW_TO_USERS), {'exception': str(e)}
    results_paragraph = ''
    if response.status_code == 200:
        json_response = response.json() # Parse the JSON response
        results_paragraph = json_response.get('summary', '') # Extract the results paragraph
        if not results_paragraph: # If the results paragraph is empty, check for exceptions
            exception = json_response.get('exception', '')
            if exception:
                results_paragraph = API_EXCEPTION_MESSAGE_SHOW_TO_USERS #exception
    else:
        results_paragraph = '{} (Response Status Code {})'.format(API_EXCEPTION_MESSAGE_SHOW_TO_USERS, response.status_code) #f'Error: {response.status_code} {response.text}' # Handle the case where the request was not successful
    
    if results_paragraph and results_paragraph is not None and len(results_paragraph) > 1 and results_paragraph[0] == ' ': # Quick solution to remove the first space character in the response paragraph
        results_paragraph = results_paragraph[1:]

    return results_paragraph, response.text # Return the results paragraph and the JSON response
    # else:
    #     data = json.dumps( # Send the Base64 encoded file content inside a JSON payload
    #         {
    #             'app_mode': app_mode,
    #             'file_id': file_id,
    #             'original_filename': original_filename,
    #             'enable_chat_history': enable_chat_history,
    #             'file_content': binary_file_content,
    #             'user_input': user_input,
    #         }
    #     )
    #     api_mock_responses = API_MOCK_RESPONSES_SUMMARIZER if app_mode == 'Document Summary' else API_MOCK_RESPONSES_CHATBOT
    #     time.sleep(random.randint(1, 10))
    #     response = random.choice(api_mock_responses)
    # results_paragraph = ''
    # if 'summary' in response:
    #     results_paragraph = response['summary']
    # if results_paragraph is None or not len(results_paragraph):
    #     if 'exception' in response and response['exception'] is not None and len(response['exception']) > 0:
    #         results_paragraph = response['exception']
    # return results_paragraph, json.dumps(response)


###############################################################################
# Update the results panel
###############################################################################
@docsapp.callback(
    Output('submit-button-loading-component', 'children'),
    Output('results-display', 'style'),
    Output('summarizer-disclaimer', 'style'),
    Output('answer-rating-button-group', 'style'),
    Output('results-display-full-text', 'children'),
    Output('results-display', 'title'),
    Output('submit-button', 'children'),
    Output('summarizer-last-submit-store', 'data'),
    Output('single-file-upload-estimate-store', 'data', allow_duplicate=True),
    Input('submit-button', 'n_clicks'),
    State('task-dropdown', 'label'),
    State('single-file-upload-estimate-store', 'data'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def get_results(submit_button_n_clicks, task_dropdown_label, single_file_upload_estimate_store):
    tz_eastern, start_time, transferDateTime, timestamp_id = get_time_info()

    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]

    domino_username = request.headers.get('domino-username')
    
    if 'submit-button' in changed_id:
        original_filename = single_file_upload_estimate_store[2]
        results_paragraph_title = 'Answered on {} for {}'.format(start_time.strftime('%Y-%m-%d %H:%M:%S'), original_filename)
        
        enable_file_saving = 0
        if not len(single_file_upload_estimate_store[3]):
            file_id = '{}-{}'.format(domino_username, timestamp_id)
            new_filename = '{}.pdf'.format(file_id)
            single_file_upload_estimate_store[3] = new_filename
            enable_file_saving = 1
        else:
            new_filename = single_file_upload_estimate_store[3]
            file_id = new_filename.rsplit('.pdf', 1)[0]

        results_json_from_api = ''

        binary_file_content = single_file_upload_estimate_store[4] #get_binary_file_content(original_filename)
        results_paragraph, results_json_from_api = get_answers_from_app_api_portal('Document Summary', file_id, original_filename, 2, binary_file_content, '')

        summarizer_last_submit_store_data = [original_filename, new_filename]
        
        if enable_file_saving:
            rename_and_save_uploaded_files_to_submit_dir(original_filename, new_filename, single_file_upload_estimate_store[4])

        generate_log(tz_eastern, start_time, transferDateTime, timestamp_id, 'summarizer', 'submitted',
                     str(summarizer_last_submit_store_data[0]), summarizer_last_submit_store_data[1], '', str(results_paragraph), str(results_json_from_api))
        return None, {'font-size': 'max(0.82vw, 10.5px)', 'whiteSpace': 'pre-wrap'}, {'font-size': 'max(0.675vw, 8.75px)'}, {}, results_paragraph, results_paragraph_title, dash.no_update, summarizer_last_submit_store_data, single_file_upload_estimate_store
    
    return None, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update


###############################################################################
# Submit the copy response log for the summarizer
###############################################################################
@docsapp.callback(
    Output('copy-results', 'color'),
    Input('copy-results', 'n_clicks'),
    State('results-display-full-text', 'children'),
    State('summarizer-last-submit-store', 'data'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def submit_copy_response(good_response_button_n_clicks, results_paragraph, summarizer_last_submit_store_data):
    tz_eastern, start_time, transferDateTime, timestamp_id = get_time_info()
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if 'copy-results' in changed_id:
        generate_log(tz_eastern, start_time, transferDateTime, timestamp_id, 'summarizer', 'copied',
                     '', summarizer_last_submit_store_data[1], '', str(results_paragraph))
    return dash.no_update


###############################################################################
# Submit the good response rating for the summarizer
###############################################################################
@docsapp.callback(
    Output('good-response', 'color'),
    Input('good-response', 'n_clicks'),
    State('results-display-full-text', 'children'),
    State('summarizer-last-submit-store', 'data'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def submit_good_response(good_response_button_n_clicks, results_paragraph, summarizer_last_submit_store_data):
    tz_eastern, start_time, transferDateTime, timestamp_id = get_time_info()

    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if 'good-response' in changed_id:
        generate_log(tz_eastern, start_time, transferDateTime, timestamp_id, 'summarizer', 'good-response',
                     '', summarizer_last_submit_store_data[1], '', str(results_paragraph))
    return dash.no_update


###############################################################################
# Submit the bad response rating for the summarizer
###############################################################################
@docsapp.callback(
    Output('bad-response', 'color'),
    Input('bad-response', 'n_clicks'),
    State('results-display-full-text', 'children'),
    State('summarizer-last-submit-store', 'data'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def submit_bad_response(bad_response_button_n_clicks, results_paragraph, summarizer_last_submit_store_data):
    tz_eastern, start_time, transferDateTime, timestamp_id = get_time_info()

    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if 'bad-response' in changed_id:
        generate_log(tz_eastern, start_time, transferDateTime, timestamp_id, 'summarizer', 'bad-response',
                     '', summarizer_last_submit_store_data[1], '', str(results_paragraph))
    return dash.no_update


###############################################################################
# Update the conversation
###############################################################################
@docsapp.callback(
    Output('display-conversation', 'children'),
    Input('store-conversation-and-file-name', 'data'),
)
@prevent_update_on_error
def update_display(store_conversation_file_name_data):
    display_conversation = []
    for text_box_index, conversation_file_name_data in enumerate(store_conversation_file_name_data):
        display_conversation.append(create_user_text_box(text_box_index, conversation_file_name_data[0], conversation_file_name_data[4], conversation_file_name_data[5], conversation_file_name_data[2], conversation_file_name_data[6]))
        display_conversation.append(create_ai_text_box(text_box_index, conversation_file_name_data[1], conversation_file_name_data[2], conversation_file_name_data[3]))
    return display_conversation


###############################################################################
# Empty the chatbot's user input field
###############################################################################
@docsapp.callback(
    Output('chatbot-user-input', 'value'),
    Input('chatbot-submit-button', 'n_clicks'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def clear_chatbot_user_input(n_clicks):
    return ''


###############################################################################
# Run the chabot and get answer
###############################################################################
@docsapp.callback(
    Output('loading-component', 'children'),
    Output('store-conversation-and-file-name', 'data'),
    Output('chatbot-submit-button-n-clicks-store', 'data', allow_duplicate=True),
    Output('single-file-upload-estimate-store', 'data', allow_duplicate=True),
    Input('chatbot-submit-button', 'n_clicks'),
    State('chatbot-user-input', 'value'),
    State('task-dropdown', 'label'),
    State('store-conversation-and-file-name', 'data'),
    State('single-file-upload-estimate-store', 'data'),
    State('chatbot-submit-button-n-clicks-store', 'data'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def run_chatbot(n_clicks, user_input, task_dropdown_label, store_conversation_file_name_data, single_file_upload_estimate_store, chatbot_submit_button_n_clicks_store):
    tz_eastern, start_time, transferDateTime, timestamp_id = get_time_info()

    domino_username = request.headers.get('domino-username')

    if user_input is None or user_input == '':
        return None, dash.no_update, dash.no_update, dash.no_update

    original_filename = single_file_upload_estimate_store[2]#uploaded_files[0]
    
    enable_file_saving = 0
    if not len(single_file_upload_estimate_store[3]):
        file_id = '{}-{}'.format(domino_username, timestamp_id)
        new_filename = '{}.pdf'.format(file_id)
        single_file_upload_estimate_store[3] = new_filename
        enable_file_saving = 1
    else:
        new_filename = single_file_upload_estimate_store[3]
        file_id = new_filename.rsplit('.pdf', 1)[0]

    results_json_from_api = ''
    enable_chat_history = 0

    binary_file_content = ''
    if chatbot_submit_button_n_clicks_store:
        enable_chat_history = 1
    else:
        binary_file_content = single_file_upload_estimate_store[4]
    #results_paragraph, results_json_from_api = get_answers_from_app_api_portal('ChatPDF', file_id, original_filename, enable_chat_history, binary_file_content, user_input)
    results_paragraph, results_json_from_api = get_answers_from_app_api_portal('ChatPDF', file_id, original_filename, 0, single_file_upload_estimate_store[4], user_input) # Just a quick fix

    if enable_file_saving:
        rename_and_save_uploaded_files_to_submit_dir(original_filename, new_filename, single_file_upload_estimate_store[4])

    store_conversation_file_name_data.append([user_input, results_paragraph, original_filename, new_filename, domino_username, start_time.strftime('%Y-%m-%d %H:%M:%S'), enable_chat_history])

    generate_log(tz_eastern, start_time, transferDateTime, timestamp_id, 'chatbot', 'submitted',
              str(single_file_upload_estimate_store[0]), new_filename, str(user_input), str(results_paragraph), str(results_json_from_api))
    return None, store_conversation_file_name_data, chatbot_submit_button_n_clicks_store + 1, single_file_upload_estimate_store


###############################################################################
# Return the file processing time estimate, in seconds
###############################################################################
def get_uploaded_file_processing_time_estimate(uploaded_file_size):
    return int(max(min(uploaded_file_size * FILE_PROCESSING_SECONDS_PER_BYTE, FILE_PROCESSING_TIME_MAX), FILE_PROCESSING_TIME_MIN))


###############################################################################
# Update file preview, chatbot message, and submit button upon file upload
###############################################################################
@docsapp.callback(
    Output('file-upload-loading-component', 'children'),
    Output('uploaded-file-preview', 'src', allow_duplicate=True),
    Output('chatbot-user-input', 'placeholder'),
    Output('chatbot-user-input', 'title'),
    Output('chatbot-user-input', 'disabled'),
    Output('submit-button', 'disabled', allow_duplicate=True),
    Output('submit-button', 'title'),
    Output('single-file-upload-info', 'children'),
    Output('single-file-upload-info', 'title'),
    Output('single-file-upload-estimate-store', 'data'),
    Output('chatbot-submit-button-n-clicks-store', 'data'),
    Output('document-snapshot-header', 'className'),
    Output('results-overview-header', 'className'),
    Output('summarizer-last-submit-store', 'data', allow_duplicate=True),
    Output('results-display', 'style', allow_duplicate=True),
    Output('summarizer-disclaimer', 'style', allow_duplicate=True),
    Output('answer-rating-button-group', 'style', allow_duplicate=True),
    Input('single-file-upload', 'filename'),
    Input('single-file-upload', 'contents'),
    Input('single-file-upload', 'last_modified'),
    State('single-file-upload-estimate-store', 'data'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def upload_a_file(latest_uploaded_file_name, latest_uploaded_file_contents, latest_uploaded_file_last_modified, single_file_upload_estimate_store):
    if latest_uploaded_file_name is None or not len(latest_uploaded_file_name):
        return None, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    if not latest_uploaded_file_name.lower().endswith('.pdf'):
        return None, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, 'File type must by PDF.', dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    if len(latest_uploaded_file_name) > UPLOAD_FILE_NAME_LENGTH_LIMIT:
        return None, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, 'Filename is too long.', dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    if latest_uploaded_file_contents.startswith('data:application/pdf;base64,'):
        uploaded_file_size = len(str(latest_uploaded_file_contents[len('data:application/pdf;base64,'):]))
    else:
        uploaded_file_size = len(str(latest_uploaded_file_contents))
    uploaded_file_size = uploaded_file_size * 3 / 4 # In Base64 encoding, every 3 bytes of binary data are represented as 4 characters
    if uploaded_file_size / 1000000.0 > UPLOAD_FILE_SIZE_LIMIT_MB - UPLOAD_FILE_SIZE_LIMIT_MB_OFFSET:
        return None, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, 'File is too large.', dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    uploaded_file_time_estimate = get_uploaded_file_processing_time_estimate(uploaded_file_size)

    filename_timestamp_id = dt.datetime.now(tz=timezone('US/Eastern'))
    filename_timestamp_readable = filename_timestamp_id.strftime('%Y-%m-%d %H:%M:%S')
    filename_timestamp_id = filename_timestamp_id.strftime('%Y%m%d%H%M%S%f')

    data = latest_uploaded_file_contents.encode('utf8').split(b';base64,')[1]
    with open(os.path.join(UPLOADED_FILES_TEMP_DIRECTORY, '{}.pdf'.format(filename_timestamp_id)), 'wb') as fp: # save a copy of the file in temp directory so that we can read content from the path later; rendering source bytes directly does not work for large files
        fp.write(base64.decodebytes(data))
    src = str('assets/{}/{}.pdf'.format(UPLOADED_FILES_TEMP_DIRECTORY_FOLDER_NAME, filename_timestamp_id))
    delete_files_in_repo(file_name='{}.pdf'.format(single_file_upload_estimate_store[5]), directories=[UPLOADED_FILES_TEMP_DIRECTORY]) # Delete the previously uploaded file from the temp directory

    latest_uploaded_file_name_truncated = latest_uploaded_file_name
    if len(latest_uploaded_file_name) > 30:
        latest_uploaded_file_name_truncated = latest_uploaded_file_name[:20]
    chatbot_user_input_placeholder_text = 'Ask something about {}...'.format(latest_uploaded_file_name_truncated)
    chatbot_user_input_title_text = 'Ask something about {}'.format(latest_uploaded_file_name)
    return None, src, chatbot_user_input_placeholder_text, chatbot_user_input_title_text, False, False, 'Submit {} to the Summarizer'.format(latest_uploaded_file_name), 'Uploaded: {}'.format(latest_uploaded_file_name), '{} was uploaded on {}'.format(latest_uploaded_file_name, filename_timestamp_readable), [uploaded_file_size, uploaded_file_time_estimate, str(latest_uploaded_file_name), '', str(latest_uploaded_file_contents), str(filename_timestamp_id)], 0, 'card-title', 'card-title pb-2', '', {'display': 'none'}, {'display': 'none'}, {'display': 'none'}


###############################################################################
# Apply the typewriter effect to the generated answer
###############################################################################
dash.clientside_callback(
    '''
    function updateTypewriter(children) {
        try {
            let continueTyping = true;
            document.getElementById('submit-button').disabled = true;
            var i = 0;
            var speed = 15;
            var txt = children;
            var result = '';
            var max_length = 4000;
            function typeWriter() {
                if (!continueTyping) {
                    document.getElementById('results-display').innerHTML = children;
                    document.getElementById('submit-button').disabled = false;
                    document.getElementById('summarizer-disclaimer').style.display = '';
                    document.getElementById('answer-rating-button-group').style.display = '';
                    return;
                }
                if (i < txt.length) {
                    document.getElementById('summarizer-disclaimer').style.display = 'none';
                    document.getElementById('answer-rating-button-group').style.display = 'none';
                    result += txt.charAt(i);
                    i++;
                    document.getElementById('results-display').innerHTML = result;
                    setTimeout(typeWriter, speed);
                } else {
                    if (document.getElementById('results-display').style.display !== 'none') {
                        document.getElementById('summarizer-disclaimer').style.display = '';
                        document.getElementById('answer-rating-button-group').style.display = '';
                    }
                    document.getElementById('submit-button').disabled = false;
                }
                var resultsPanel = document.getElementById('results-panel');
                resultsPanel.scrollTop = resultsPanel.scrollHeight;
            }
            
            document.getElementById('results-display').addEventListener('click', function() {
                continueTyping = false;
            });

            document.getElementById('single-file-upload-wrapper').addEventListener('click', function() {
                continueTyping = false;
            });

            document.getElementById('single-file-upload-wrapper').addEventListener('drop', function() {
                continueTyping = false;
            });

            if (txt.length > max_length) {
                document.getElementById('results-display').innerHTML = txt;
                document.getElementById('submit-button').disabled = false;
            } else {
                typeWriter();
            }
        } catch (error) {
            document.getElementById('results-display').innerHTML = children;
            document.getElementById('submit-button').disabled = false;
            document.getElementById('summarizer-disclaimer').style.display = '';
            document.getElementById('answer-rating-button-group').style.display = '';
            return window.dash_clientside.no_update;
        }
    }
    ''',
    Output('results-display', 'children', allow_duplicate=True),
    Input('results-display-full-text', 'children'),
    prevent_initial_call=True,
)


###############################################################################
# Apply the typewriter effect to the chatbot's response
###############################################################################
dash.clientside_callback(
    '''
    function updateTypewriterChatbot(children) {
        try {
            let continueTyping = true;
            var current_index = children.length / 2 - 1;
            var elementId = '{"index":' + current_index + ',"type":"chatbot-text-card"}';
            var element = document.getElementById(elementId);
            if (element === null) {
                return window.dash_clientside.no_update;
            }

            var i = 0;
            var speed = 15;
            var txt = document.getElementById(elementId).innerHTML;
            var result = '';
            var max_length = 4000;
            function typeWriter() {
                if (!continueTyping) {
                    document.getElementById(elementId).innerHTML = txt;
                    document.getElementById(elementId).style.display = '';
                    document.getElementById('{"index":' + current_index + ',"type":"chatbot-text-card-buttons"}').style.visibility = '';
                    return;
                }
                if (i < txt.length) {
                    result += txt.charAt(i);
                    i++;
                    document.getElementById(elementId).innerHTML = result;
                    document.getElementById(elementId).style.display = '';
                    setTimeout(typeWriter, speed);
                } else {
                    if (document.getElementById(elementId).style.display !== 'none') {
                        document.getElementById('{"index":' + current_index + ',"type":"chatbot-text-card-buttons"}').style.visibility = '';
                    }
                }
            } 

            document.getElementById(elementId).addEventListener('click', function() {
                continueTyping = false;
            });
            
            if (txt.length > max_length) {
                document.getElementById(elementId).innerHTML = txt;
                document.getElementById(elementId).style.display = '';
                document.getElementById('{"index":' + current_index + ',"type":"chatbot-text-card-buttons"}').style.visibility = '';
                var displayConverstation = document.getElementById('display-conversation');
                displayConverstation.scrollTop = displayConverstation.scrollHeight;
            } else {
                typeWriter();
            }
        } catch (error) {
            var current_index = children.length / 2 - 1;
            var elementId = '{"index":' + current_index + ',"type":"chatbot-text-card"}';
            document.getElementById(elementId).innerHTML = txt;
            document.getElementById(elementId).style.display = '';
            document.getElementById('{"index":' + current_index + ',"type":"chatbot-text-card-buttons"}').style.visibility = '';
            return window.dash_clientside.no_update;
        }
        
    }
    ''',
    Output('results-display', 'lang', allow_duplicate=True),
    Input('display-conversation', 'children'),
    prevent_initial_call=True,
)


###############################################################################
# Remove user input focus
###############################################################################
dash.clientside_callback(
    '''
    function removeFocus(n_clicks) {
        var element = document.getElementById('chatbot-user-input');
        if (element === null) {
            return window.dash_clientside.no_update;
        }

        if (n_clicks > 0) {
            document.getElementById('chatbot-user-input').blur();
        }
    }
    ''',
    Output('chatbot-user-input', 'n_blur'),
    Input('chatbot-submit-button', 'n_clicks'),
    prevent_initial_call=True
)


###############################################################################
# Fill the copy results icon on mouseover event
###############################################################################
@docsapp.callback(
    Output('copy-results-icon', 'className'),
    Input('copy-results-icon-popover', 'is_open'),
)
@prevent_update_on_error
def update_copy_results_icon(is_open):
    return 'bi bi-clipboard-fill' if is_open else 'bi bi-clipboard'


###############################################################################
# Fill the good response icon on mouseover event
###############################################################################
@docsapp.callback(
    Output('good-response-icon', 'className'),
    Input('good-response-icon-popover', 'is_open'),
)
@prevent_update_on_error
def update_good_response_icon(is_open):
    return 'bi bi-hand-thumbs-up-fill' if is_open else 'bi bi-hand-thumbs-up'


###############################################################################
# Fill the bad response icon on mouseover event
###############################################################################
@docsapp.callback(
    Output('bad-response-icon', 'className'),
    Input('bad-response-icon-popover', 'is_open'),
)
@prevent_update_on_error
def update_bad_response_icon(is_open):
    return 'bi bi-hand-thumbs-down-fill' if is_open else 'bi bi-hand-thumbs-down'


###############################################################################
# Fill the chatbot's copy results icon on mouseover event
###############################################################################
@docsapp.callback(
    Output({'type': 'chatbot-copy-results-icon', 'index': MATCH}, 'className'),
    Input({'type': 'chatbot-copy-results-icon-popover', 'index': MATCH}, 'is_open'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def update_chatbot_copy_results_icon(is_open):
    return 'bi bi-clipboard-fill' if is_open else 'bi bi-clipboard'


###############################################################################
# Fill the chatbot's good response (thumbs up) icon on mouseover event
###############################################################################
@docsapp.callback(
    Output({'type': 'chatbot-good-response-icon', 'index': MATCH}, 'className'),
    Input({'type': 'chatbot-good-response-icon-popover', 'index': MATCH}, 'is_open'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def update_chatbot_good_response_icon(is_open):
    return 'bi bi-hand-thumbs-up-fill' if is_open else 'bi bi-hand-thumbs-up'


###############################################################################
# Fill the chatbot's bad response (thumbs down) icon on mouseover event
###############################################################################
@docsapp.callback(
    Output({'type': 'chatbot-bad-response-icon', 'index': MATCH}, 'className'),
    Input({'type': 'chatbot-bad-response-icon-popover', 'index': MATCH}, 'is_open'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def update_chatbot_bad_response_icon(is_open):
    return 'bi bi-hand-thumbs-down-fill' if is_open else 'bi bi-hand-thumbs-down'


###############################################################################
# Automatically grow and shrink the height of the chatbot's user input text 
# area
###############################################################################
docsapp.clientside_callback(
    '''
    function autoGrow(element) {
        element = document.getElementById('chatbot-user-input');
        if (element && element.value) {
            //element.style.height = 'auto';
            element.style.height = 0;
            element.style.height = (element.scrollHeight) + 'px';
            resultsPanel = document.getElementById('results-panel');
            resultsPanel.scrollTop = (element.selectionStart / element.value.length) * element.scrollHeight;
        }
        else
            element.style.height = '';
    }
    ''',
    Output('chatbot-user-input', 'name'),
    Input('chatbot-user-input', 'value'),
    prevent_initial_call=True
)


###############################################################################
# If the Enter key is pressed while focusing on the text input field but the 
# Shift key is not pressed at the same time, click the chatbot's submit button
###############################################################################
docsapp.clientside_callback(
    '''
        function(id) {
            document.addEventListener('keydown', function(event) {
                var chatbotUserInput = document.getElementById('chatbot-user-input');
                if (document.activeElement === chatbotUserInput){
                    if (event.keyCode === 13) {
                        if (event.shiftKey) {
                            event.stopPropagation();
                        } else {
                            document.getElementById('chatbot-submit-button').click();
                        }
                    }
                }
            });
            return window.dash_clientside.no_update
        }
    ''',
    Output('chatbot-user-input', 'id'),
    Input('chatbot-user-input', 'id')
)


###############################################################################
# If mouse enters the file upload area or leave the current window, disable 
# the submit buttons and remove focus; give focus back after some time
###############################################################################
docsapp.clientside_callback(
    '''
        function(id) {
            document.getElementById('single-file-upload-wrapper').addEventListener('mouseenter', function() {
                if (typeof timeoutId !== 'undefined') clearTimeout(timeoutId);
                document.getElementById('submit-button').style.pointerEvents = 'none';
                document.getElementById('chatbot-user-input-group').style.pointerEvents = 'none';
                document.activeElement.blur();
            });
            document.getElementById('single-file-upload-wrapper').addEventListener('mouseleave', function() {
                timeoutId = setTimeout(function() {
                    document.getElementById('submit-button').style.pointerEvents = '';
                    document.getElementById('chatbot-user-input-group').style.pointerEvents = '';
                }, 1000);
            });
            document.addEventListener('mouseleave', function() {
                document.activeElement.blur();
            });
            return window.dash_clientside.no_update       
        }
    ''',
    Output('single-file-upload', 'id'),
    Input('single-file-upload', 'id')
)


###############################################################################
# Calculate remaining time and show on progress bar
###############################################################################
docsapp.clientside_callback(
    ''' 
        function waitForElement(n_clicks, data_store) {
            var submitButtonSpinner = document.getElementById('submit-button-loading-component-spinner');
            if (submitButtonSpinner !== null) {
                submitButtonSpinner.style['-webkit-animation-duration'] = data_store[1] + 's';
                submitButtonSpinner.style['animation-duration'] = data_store[1] + 's';
                let countdown = data_store[1];
                submitButtonSpinner.innerHTML = '<br><br>Your file is being analyzed by AI...<br><br>Remaining time estimate: Calculating...';
                
                function updateCountdown() {
                    if (countdown > 0) {
                        countdown--;
                        submitButtonSpinner.innerHTML = '<br><br>Your file is being analyzed by AI...<br><br>Remaining time estimate: ' + countdown + 's';
                    } else {
                        submitButtonSpinner.innerHTML = '<br><br>Your file is being analyzed by AI...<br><br>File processing is taking longer than usual. Please wait a moment or refresh the page and try again.';
                        clearInterval(interval); // Stop the countdown
                    }
                }
                const interval = setInterval(updateCountdown, 1000);
            } else {
                setTimeout(waitForElement, 1000, n_clicks, data_store); // Check again in 1000 milliseconds
            }
        }
    ''',
    Output('submit-button-loading-component', 'id'),
    Input('submit-button', 'n_clicks'),
    State('single-file-upload-estimate-store', 'data'),
    prevent_initial_call=True
)


###############################################################################
# Calculate remaining time and show on progress bar for the chatbot
###############################################################################
docsapp.clientside_callback(
    ''' 
        function waitForElement(n_clicks, data_store) {
            var submitButtonSpinner = document.getElementById('loading-component-spinner');
            if (submitButtonSpinner !== null) {
                submitButtonSpinner.style['-webkit-animation-duration'] = data_store[1] + 's';
                submitButtonSpinner.style['animation-duration'] = data_store[1] + 's';
                let countdown = data_store[1];
                submitButtonSpinner.innerHTML = '<br><br>Your file is being analyzed by AI...<br><br>Remaining time estimate: Calculating...';
                
                function updateCountdown() {
                    if (countdown > 0) {
                        countdown--;
                        submitButtonSpinner.innerHTML = '<br><br>Your file is being analyzed by AI...<br><br>Remaining time estimate: ' + countdown + 's';
                    } else {
                        submitButtonSpinner.innerHTML = '<br><br>Your file is being analyzed by AI...<br><br>File processing is taking longer than usual. Please wait a moment or refresh the page and try again.';
                        clearInterval(interval); // Stop the countdown
                    }
                }
                const interval = setInterval(updateCountdown, 1000);
            } else {
                setTimeout(waitForElement, 1000, n_clicks, data_store); // Check again in 1000 milliseconds
            }
        }
    ''',
    Output('loading-component', 'id'),
    Input('chatbot-submit-button', 'n_clicks'),
    State('single-file-upload-estimate-store', 'data'),
    prevent_initial_call=True
)


###############################################################################
# Toggle the user guide modal
###############################################################################
@docsapp.callback(
    Output('user-guide-modal', 'is_open'),
    Input('open-user-guide-modal-button', 'n_clicks'),
    State('user-guide-modal', 'is_open'),
    prevent_initial_call=True,
)
@prevent_update_on_error
def toggle_user_guide_modal(open_user_guide_modal_button_n_clicks, user_guide_modal_is_open):
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if 'open-user-guide-modal-button' in changed_id:
        return True
    return False


###############################################################################
# Utilize the Flask's error handling mechanism
###############################################################################
@server.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, dash.exceptions.PreventUpdate):
        return '', 200
    tz_eastern, start_time, transferDateTime, timestamp_id = get_time_info()
    generate_exception_log(tz_eastern, start_time, transferDateTime, timestamp_id, str(e))
    return str(e), 500


###############################################################################
# Main
###############################################################################
if __name__ == '__main__':
    #if RUN_ON_LOCAL:
    docsapp.run_server(debug=False)
    #else:
      #  app.run_server(debug=False, host='0.0.0.0', port=8888)

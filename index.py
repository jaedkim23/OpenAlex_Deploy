import os
import pandas as pd
from dotenv import load_dotenv
import requests
import datetime
import numpy as np

import dash
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
from dash import dash_table

current_year = datetime.datetime.now().year

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
# #####################################
# # Add your data
# #####################################

CAS  = pd.read_pickle("Data/CAS_mod.pkl")
CAS.columns = CAS.columns.str.lower()
search_words = ['Professor', 'Assistant Professor', 'Associate Professor', 'Lecturer']
pattern = '|'.join(search_words)
emp = CAS[CAS['position'].str.contains(pattern, case=False, na=False)]

id_lookup = pd.read_pickle("Data/id_lookup.pkl")

#####################################
load_dotenv()
import clarivate.wos_starter.client
from clarivate.wos_starter.client.rest import ApiException
api = os.getenv("WOS_API")
configuration = clarivate.wos_starter.client.Configuration(
    host = "http://api.clarivate.com/apis/wos-starter/v1"
)
configuration.api_key['ClarivateApiKeyAuth'] = api
api_inst= clarivate.wos_starter.client.DocumentsApi(clarivate.wos_starter.client.ApiClient(configuration))
#####################################


#####################################
# Styles & Colors
#####################################

NAVBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "12rem",
    "padding": "2rem 1rem",
    "background-color": "#f8f9fa",
}

CONTENT_STYLE = {
    "margin-top":'2rem',
    "margin-left": "18rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}

SIDEBAR_STYLE = {
    "position": "fixed",  # comment this out
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "16rem",
    "padding": "2rem 1rem",
    "background-color": "#f8f9fa",
}

#####################################
# Create Auxiliary Components Here
#####################################


sidebar = html.Div(
    [
        html.H5("Search employee records", className="display-10",style={'textAlign':'center'}),
        html.Hr(),
        html.P(
            "Employee:", className="lead"
        ),
        dcc.Dropdown(
                        id="employee_input_value",
                        options=emp['preferred_name'].to_list(),
                        value=emp['preferred_name'].to_list()[0],
                    ),
        dcc.Dropdown(
                        id="min_year_select",
                        options = np.arange(1985, current_year+1).tolist(),
                        value = 2000,
                    ),      
        html.Hr(),
    ],
    style=SIDEBAR_STYLE,
)


#####################################
# Create Page Layouts Here
#####################################

### Layout 1
layout1 = html.Div([html.Div(id="emp_info2"),  html.Div([html.H4("Results below:"), html.Hr()]), html.Div(id="emp_info1")])

layout2 = html.Div(id="emp_table_tab1")

layout3 = html.Div(id="emp_table_tab2")

layout4 = html.Div(id="emp_summary")

content = html.Div([html.H1("Records"),
                    html.Hr(),
                    dcc.Tabs(id="tabs-main", value="tab-1", children=[
                            dcc.Tab(layout1,
                                    label = "Summary",
                                    value = 'tab-1',
                                    ),
                            dcc.Tab(layout2,
                                    label = "WOS",
                                    value = 'tab-2',
                                    ),
                            dcc.Tab(layout3,
                                    label = "OpenAlex",
                                    value = 'tab-3',
                                    ),
                            dcc.Tab(layout4,
                                    label = "Common List",
                                    value = 'tab-4',
                                    ),
                                ]),
                ]
        )

app.layout = html.Div([dbc.Col(sidebar), dbc.Col(content, style=CONTENT_STYLE, width=9)])


######################################################################
## Callbacks
######################################################################

@app.callback(Output("content", "children"), [Input("tabs-main", 'value')])
def render_content(tabX):
    if tabX=="tab-1":
        return layout1
    elif tabX=="tab-2":
        return layout2
    elif tabX=="tab-3":
        return layout3
    elif tabX=="tab-4":
        return layout4
    else:
        return html.P("Error")

@app.callback(Output('emp_info2', 'children'),
              [Input('employee_input_value', 'value')])
def update_emp_info_page(value):
    first_name = value.split(' ')[0]
    last_name = value.split(' ')[1]
    author_record = CAS[(CAS['first_name']==first_name) & (CAS['last_name']==last_name)]
    author_record = author_record[['first_name','last_name','position','department','college']]
    return dash_table.DataTable(author_record.to_dict('records'), [{"name": i, "id": i} for i in author_record.columns], 
                                row_selectable="multi",editable=False, 
                                style_data={'whiteSpace': 'normal', 'height': 'auto'})

@app.callback(Output('emp_info1', 'children'),
              [Input('employee_input_value', 'value'),
               Input('min_year_select', 'value')])
def update_emp_summary_table(value, year_select):
    author_record = find_lookup_record(value)
    author_wos = author_record['wos_id'].to_list()
    if len(author_wos)==0:
        df_wos = 0
    elif None not in author_wos:
        df_wos = create_record_tbl(author_wos, api_inst)
        df_wos = df_wos[df_wos['publishYear']>=year_select]
    else:
        df_wos = 0
    
    df_wos_n = 0
    if isinstance(df_wos, pd.DataFrame):
        if (len(df_wos)!=0):
            df_wos_n = len(df_wos)
    
    if len(author_record['alex_id'])==0:
        author_alex = None
    elif len(author_record['alex_id'])>1:
        author_alex = author_record['alex_id']
        author_alex = author_alex.iloc[0]
    else:
        author_alex = author_record['alex_id'].item()
    
    if author_alex != None:
        df_alex = create_record_tbl_alex(author_alex)
        df_alex = df_alex[df_alex['work_publication_year']>=year_select]
    else: 
        df_alex = 0
    
    df_alex_n = 0
    if isinstance(df_alex, pd.DataFrame):
        if (len(df_alex)!=0):
            df_alex_n = len(df_alex)

    unique_recs = find_common_records(df_wos, df_alex)
    if not isinstance(unique_recs, pd.DataFrame):
        if unique_recs==0:
            df = pd.DataFrame({'Records in WOS': [0], 'Records in OpenAlex': [0], 'Unique Records': [0]}) 
    elif isinstance(unique_recs, pd.DataFrame) & (len(unique_recs)==0):
        df = pd.DataFrame({'Records in WOS': [0], 'Records in OpenAlex': [0], 'Unique Records': [0]})
    elif isinstance(unique_recs, pd.DataFrame):
        df = pd.DataFrame({'Records in WOS': [df_wos_n], 'Records in OpenAlex': [df_alex_n], 'Unique Records': [len(unique_recs)]})
    else:
        df = pd.DataFrame({'Records in WOS': [0], 'Records in OpenAlex': [0], 'Unique Records': [0]})
    return dash_table.DataTable(df.to_dict('records'), [{"name": i, "id": i} for i in df.columns], 
                                row_selectable="multi",editable=False, 
                                style_data={'whiteSpace': 'normal', 'height': 'auto'})

@app.callback(Output('emp_summary', 'children'),
              [Input('employee_input_value', 'value'),
               Input('min_year_select', 'value')])
def update_emp_info(value, year_select):
    author_record = find_lookup_record(value)
    author_wos = author_record['wos_id'].to_list()
    if len(author_wos)==0:
        df_wos = 0
    elif None not in author_wos:
        df_wos = create_record_tbl(author_wos, api_inst)
        df_wos = df_wos[df_wos['publishYear']>=year_select]
    else:
        df_wos = 0
    
    if len(author_record['alex_id'])==0:
        author_alex = None
    elif len(author_record['alex_id'])>1:
        author_alex = author_record['alex_id']
        author_alex = author_alex.iloc[0]
    else:
        author_alex = author_record['alex_id'].item()
    
    if author_alex != None:
        df_alex = create_record_tbl_alex(author_alex)
        df_alex = df_alex[df_alex['work_publication_year']>=year_select]
    else: 
        df_alex = 0
    
    unique_recs = find_common_records(df_wos, df_alex)
    if not isinstance(unique_recs, pd.DataFrame):
        if unique_recs==0:
            df_common = pd.DataFrame({'Records in WOS': [0], 'Records in OpenAlex': [0], 'Unique Records': [0]}) 
    elif isinstance(unique_recs, pd.DataFrame) & (len(unique_recs)==0):
        df_common = pd.DataFrame({'Records in WOS': [0], 'Records in OpenAlex': [0], 'Unique Records': [0]})
    elif isinstance(unique_recs, pd.DataFrame):
        df_common = df_wos.iloc[0].copy()
        df_common['web_source'] = 'WOS'
        df_common = df_common.to_frame().transpose()
        
        for work in range(len(unique_recs)):
            work_n = unique_recs.iloc[work]
            if work_n['title'] in df_wos['title'].str.lower().to_list():
                df_common_add = df_wos[(df_wos['title'].str.lower()==work_n['title']) & (df_wos['publishYear']==work_n['publishYear'])].copy() 
                df_common_add['web_source'] = 'WOS'
                df_common = pd.concat([df_common, df_common_add], axis=0, ignore_index=True)
            elif work_n['title'] in df_alex['work_title'].str.lower().to_list():
                df_common_add_alex = df_alex[(df_alex['work_title'].str.lower()==work_n['title']) & (df_alex['work_publication_year']==work_n['publishYear'])].copy()
                df_common_add = pd.DataFrame({'work_id':df_common_add_alex['work_id'], 'title':df_common_add_alex['work_title'], 'source':df_common_add_alex['work_source'], 'publishYear':df_common_add_alex['work_publication_year'], 'web_source':'OpenAlex'})
                df_common = pd.concat([df_common, df_common_add], axis=0, ignore_index=True)
        
        df_common = df_common.drop(df_common.index[0]).reset_index(drop=True)
    else:
        df_common = pd.DataFrame({'Records in WOS': [0], 'Records in OpenAlex': [0], 'Unique Records': [0]})
    
    return dash_table.DataTable(df_common.to_dict('records'), [{"name": i, "id": i} for i in df_common.columns], 
                                row_selectable="multi",editable=False, 
                                style_data={'whiteSpace': 'normal', 'height': 'auto'})


@app.callback(Output('emp_table_tab1', 'children'),
              [Input('employee_input_value', 'value'),
               Input('min_year_select', 'value')])
def update_emp_wos(value, year_select):
    author_wos = find_lookup_record(value)
    author_wos = author_wos['wos_id'].to_list()
    if len(author_wos)==0:
        df = pd.DataFrame({'Number of records':[0]})
    elif None not in author_wos:
        df = create_record_tbl(author_wos, api_inst)
        df = df[df['publishYear']>=year_select]
    else:
        df = pd.DataFrame({'Number of records':[0]})
    
    return dash_table.DataTable(df.to_dict('records'), [{"name": i, "id": i} for i in df.columns], 
                                row_selectable="multi",editable=False, 
                                style_data={'whiteSpace': 'normal', 'height': 'auto'})


@app.callback(Output('emp_table_tab2', 'children'),
              [Input('employee_input_value', 'value'),
               Input('min_year_select', 'value')])
def update_emp_alex(value, year_select):
    author_alex = find_lookup_record(value)
    if len(author_alex['alex_id'])==0:
        author_alex = None
    elif len(author_alex['alex_id'])>1:
        author_alex = author_alex['alex_id']
        author_alex = author_alex.iloc[0]
    else:
        author_alex = author_alex['alex_id'].item()

    
    if author_alex != None:
        df = create_record_tbl_alex(author_alex)
        df = df[df['work_publication_year']>=year_select]
    else: 
        df = pd.DataFrame({'Number of records':[0]})
    
    return dash_table.DataTable(df.to_dict('records'), [{"name": i, "id": i} for i in df.columns], 
                                row_selectable="multi",editable=False,
                                style_data={'whiteSpace': 'normal', 'height': 'auto'})


# @app.callback(Output('worker_table_active', 'data'),
#               [Input('employee_input_value', 'value')])
# def update_emp_table(value):
#     author_wos = find_lookup_record(value)
#     df = create_record_tbl(author_wos, api_inst)
#     return df.to_json(date_format='iso', orient='split')


# @app.callback(Output("worker_table_tab1", 'children'),
#               Input('worker_table_active', 'data'))
# def show_emp_table_tabl(df):
#     df = pd.read_json(df, orient='split')
#     return dash_table.DataTable(df.to_dict('records'), [{"name": i, "id": i} for i in df.columns], 
#                                 row_selectable="multi",editable=False)


def create_record_tbl_alex(author_id_in):
    ### WOS records
    ### Check if there is no matching WOS id first
    usd_alex_id = "https://openalex.org/I160856358"
    pub_alex = get_open_alex_data_ai(author_id_in)
    pub_alex = pub_alex.loc[pub_alex['institution_id'] == usd_alex_id]
    pub_alex = pub_alex[['work_id', 'work_title', 'work_publication_year', 'work_source']]
    return pub_alex

def create_record_tbl(author_id_in, api_param_in):
    ### WOS records
    ### Check if there is no matching WOS id first
    pub_df=[]
    for author_n in range(len(author_id_in)):
        author_wos_id = author_id_in[author_n]
        rec1_df = get_wos_data_ai(api_param_in, 1, author_wos_id).to_dict()
        n_records = rec1_df['metadata']['total']
        ### if there is more than 1 record:
        if n_records > 1:
            n_limit = rec1_df['metadata']['limit']
            page = range(1, n_records//n_limit+2)
            data = []
            for page_n in page:
                rec1_df = get_wos_data_ai(api_param_in, page_n, author_wos_id).to_dict() 
                for index in range(len(rec1_df['hits'])):
                    if 'doi' in rec1_df['hits'][index]['identifiers']:
                        doi = rec1_df['hits'][index]['identifiers']['doi']
                    else:
                        doi = None
                    if 'issn' in rec1_df['hits'][index]['identifiers']:
                        issn = rec1_df['hits'][index]['identifiers']['issn']
                    else:
                        issn = None
                    if 'eissn' in rec1_df['hits'][index]['identifiers']:
                        eissn = rec1_df['hits'][index]['identifiers']['eissn']
                    else:
                        eissn = None
                    pub_df.append({
                        'work_id': rec1_df['hits'][index]['uid'].split(':')[1],
                        'title': rec1_df['hits'][index]['title'],
                        'source': rec1_df['hits'][index]['source']['sourceTitle'],
                        'publishYear': rec1_df['hits'][index]['source']['publishYear'],
                        'doi': doi,
                        'issn': issn,
                        'eissn': eissn,
                        })
    pub_df = pd.DataFrame(pub_df)
    return pub_df

def get_wos_data_au(api_instance, page_n, author):
    q = f'AU={author} AND OG=University of San Diego AND PY=(2000-{current_year})' # str | Web of Science advanced [advanced search query builder](https://webofscience.help.clarivate.com/en-us/Content/advanced-search.html). The supported field tags are listed in description.
    db = 'WOS' # str | Web of Science Database abbreviation * WOS - Web of Science Core collection * BIOABS - Biological Abstracts * BCI - BIOSIS Citation Index * BIOSIS - BIOSIS Previews * CCC - Current Contents Connect * DIIDW - Derwent Innovations Index * DRCI - Data Citation Index * MEDLINE - MEDLINE The U.S. National Library of Medicine® (NLM®) premier life sciences database. * ZOOREC - Zoological Records * PPRN - Preprint Citation Index * WOK - All databases  (optional) (default to 'WOS')
    limit = 50 # int | set the limit of records on the page (1-50) (optional) (default to 10)
    page = page_n # int | set the result page (optional) (default to 1)
    sort_field = 'LD+D' # str | Order by field(s). Field name and order by clause separated by '+', use A for ASC and D for DESC, ex: PY+D. Multiple values are separated by comma. Supported fields:  * **LD** - Load Date * **PY** - Publication Year * **RS** - Relevance * **TC** - Times Cited  (optional)
    modified_time_span = None # str | Defines a date range in which the results were most recently modified. Beginning and end dates must be specified in the yyyy-mm-dd format separated by '+' or ' ', e.g. 2023-01-01+2023-12-31. This parameter is not compatible with the all databases search, i.e. db=WOK is not compatible with this parameter. (optional)
    tc_modified_time_span = None # str | Defines a date range in which times cited counts were modified. Beginning and end dates must be specified in the yyyy-mm-dd format separated by '+' or ' ', e.g. 2023-01-01+2023-12-31. This parameter is not compatible with the all databases search, i.e. db=WOK is not compatible with this parameter. (optional)
    detail = None # str | it will returns the full data by default, if detail=short it returns the limited data (optional)

    try:
        # Query Web of Science documents 
        api_response = api_instance.documents_get(q, db=db, limit=limit, page=page, sort_field=sort_field, modified_time_span=modified_time_span, tc_modified_time_span=tc_modified_time_span, detail=detail)
        return api_response
        # print("The response of DocumentsApi->documents_get:\n")
        # pprint(api_response)
    except ApiException as e:
        return print("Exception when calling DocumentsApi->documents_get: %s\n" % e)
    
def get_wos_data_ai(api_instance, page_n, author_id):
    q = f'AI={author_id}' # str | Web of Science advanced [advanced search query builder](https://webofscience.help.clarivate.com/en-us/Content/advanced-search.html). The supported field tags are listed in description.
    db = 'WOS' # str | Web of Science Database abbreviation * WOS - Web of Science Core collection * BIOABS - Biological Abstracts * BCI - BIOSIS Citation Index * BIOSIS - BIOSIS Previews * CCC - Current Contents Connect * DIIDW - Derwent Innovations Index * DRCI - Data Citation Index * MEDLINE - MEDLINE The U.S. National Library of Medicine® (NLM®) premier life sciences database. * ZOOREC - Zoological Records * PPRN - Preprint Citation Index * WOK - All databases  (optional) (default to 'WOS')
    limit = 50 # int | set the limit of records on the page (1-50) (optional) (default to 10)
    page = page_n # int | set the result page (optional) (default to 1)
    sort_field = 'LD+D' # str | Order by field(s). Field name and order by clause separated by '+', use A for ASC and D for DESC, ex: PY+D. Multiple values are separated by comma. Supported fields:  * **LD** - Load Date * **PY** - Publication Year * **RS** - Relevance * **TC** - Times Cited  (optional)
    modified_time_span = None # str | Defines a date range in which the results were most recently modified. Beginning and end dates must be specified in the yyyy-mm-dd format separated by '+' or ' ', e.g. 2023-01-01+2023-12-31. This parameter is not compatible with the all databases search, i.e. db=WOK is not compatible with this parameter. (optional)
    tc_modified_time_span = None # str | Defines a date range in which times cited counts were modified. Beginning and end dates must be specified in the yyyy-mm-dd format separated by '+' or ' ', e.g. 2023-01-01+2023-12-31. This parameter is not compatible with the all databases search, i.e. db=WOK is not compatible with this parameter. (optional)
    detail = None # str | it will returns the full data by default, if detail=short it returns the limited data (optional)

    try:
        # Query Web of Science documents 
        api_response = api_instance.documents_get(q, db=db, limit=limit, page=page, sort_field=sort_field, modified_time_span=modified_time_span, tc_modified_time_span=tc_modified_time_span, detail=detail)
        return api_response
        # print("The response of DocumentsApi->documents_get:\n")
        # pprint(api_response)
    except ApiException as e:
        return print("Exception when calling DocumentsApi->documents_get: %s\n" % e)

def get_open_alex_data_ai(id_in):
    endpoint = 'authors'
    filtered_works_url = f'https://api.openalex.org/works?filter=author.id:{id_in}'
    page_with_results = requests.get(filtered_works_url).json()
    # page_with_results['meta']
    # works = page_with_results['results']

    cursor_alex = '*'

    select = ",".join((
        'id',
        'ids',
        'title',
        'display_name',
        'publication_year',
        'publication_date',
        'primary_location',
        'open_access',
        'authorships',
        'cited_by_count',
        'is_retracted',
        'is_paratext',
        'updated_date',
        'created_date',
    ))

    # loop through pages
    works = []
    loop_index = 0
    while cursor_alex:
        # set cursor value and request page from OpenAlex
        url = f'{filtered_works_url}&select={select}&cursor={cursor_alex}'
        page_with_results = requests.get(url).json()
        
        results = page_with_results['results']
        works.extend(results)

        # update cursor to meta.next_cursor
        cursor_alex = page_with_results['meta']['next_cursor']
        loop_index += 1
        if loop_index in [5, 10, 20, 50, 100] or loop_index % 500 == 0:
            print(f'{loop_index} api requests made so far')
    print(f'done. made {loop_index} api requests. collected {len(works)} works')

    data = []
    for work in works:
        if work['primary_location'] != None:
            if work['primary_location']["source"] != None:
                source_display_name = work['primary_location']['source']['display_name']
        else:
            source_display_name = None
        for authorship in work['authorships']:
            if authorship:
                author = authorship['author']
                author_id = author['id'] if author else None
                author_name = author['display_name'] if author else None
                author_position = authorship['author_position']
                for institution in authorship['institutions']:
                    if institution:
                        institution_id = institution['id']
                        institution_name = institution['display_name']
                        institution_country_code = institution['country_code']
                        data.append({
                            'work_id': work['id'],
                            'work_title': work['title'],
                            'work_display_name': work['display_name'],
                            'work_publication_year': work['publication_year'],
                            'work_publication_date': work['publication_date'],
                            'work_source': source_display_name,
                            'author_id': author_id,
                            'author_name': author_name,
                            'author_position': author_position,
                            'institution_id': institution_id,
                            'institution_name': institution_name,
                            'institution_country_code': institution_country_code,
                        })
    pub_alex = pd.DataFrame(data)
    pub_alex = pub_alex[pub_alex['author_id'] == 'https://openalex.org/'+id_in]
    return pub_alex



def find_lookup_record(author_in):
    author_record = emp[emp['preferred_name']==author_in]
    author_record = id_lookup[id_lookup['emp_id']==int(author_record['emp_id'].values[0])]
    # author_record = author_record['wos_id'].to_list()
    return author_record


def find_common_records(df1_wos, df2_alex):
    if isinstance(df1_wos, pd.DataFrame):
        df_wos_sub = df1_wos[['title','source','publishYear']].copy()
        df_wos_sub['title'] = df_wos_sub['title'].str.lower()
        df_wos_sub['source'] = df_wos_sub['source'].str.lower()    
    else:
        df_wos_sub = 0
    
    if isinstance(df2_alex, pd.DataFrame):
        df_alex_sub = df2_alex[['work_title','work_source','work_publication_year']].copy()
        df_alex_sub['work_source'] = df_alex_sub['work_source'].str.lower()
        df_alex_sub['work_title'] = df_alex_sub['work_title'].str.lower()
        df_alex_sub.columns = ['title','source','publishYear']
    else:
        df_alex_sub = 0

    if (isinstance(df_wos_sub, pd.DataFrame)) and (isinstance(df_alex_sub, pd.DataFrame)):
        df_combined = pd.concat([df_wos_sub, df_alex_sub], axis=0)
        df_combined = df_combined.drop_duplicates(subset=['title','publishYear'], keep=False)
    elif isinstance(df_wos_sub, pd.DataFrame) and (df_alex_sub == 0):
        df_combined = df_wos_sub
    elif (df_wos_sub == 0) and (isinstance(df_alex_sub, pd.DataFrame)):
        df_combined = df_alex_sub
    else:
        df_combined = 0
    return df_combined


server = app.server

if __name__ == '__main__':
    app.run(debug=True)

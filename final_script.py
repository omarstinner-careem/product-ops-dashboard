import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import plotly.express as px
from datetime import datetime
import streamlit as st
import re
import calendar
from plotly.graph_objs import Figure
from dateutil.relativedelta import relativedelta
from collections import OrderedDict
from streamlit_gsheets import GSheetsConnection
import gspread
import json
from google.oauth2.service_account import Credentials

st.set_page_config(layout="wide")

# conn = st.experimental_connection("gsheets", type=GSheetsConnection)

# data1 = conn.read(worksheet="Experiments")
# data2 = conn.read(worksheet="Weekly")

# Function to fetch Google Sheets data dynamically
@st.cache_data(ttl=1)  

def load_data(sheet_name):
    creds_dict = st.secrets["connections"]["gsheets"]  # ✅ Ensure correct access

    creds_info = {
        "type": creds_dict["type"],
        "project_id": creds_dict["project_id"],
        "private_key_id": creds_dict["private_key_id"],
        "private_key": creds_dict["private_key"].replace('\\n', '\n'),
        "client_email": creds_dict["client_email"],
        "client_id": creds_dict["client_id"],
        "auth_uri": creds_dict["auth_uri"],
        "token_uri": creds_dict["token_uri"],
        "auth_provider_x509_cert_url": creds_dict["auth_provider_x509_cert_url"],
        "client_x509_cert_url": creds_dict["client_x509_cert_url"]
    }

    # ✅ Authenticate
    creds = Credentials.from_service_account_info(creds_info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
    client = gspread.authorize(creds)

    # ✅ Open spreadsheet and worksheet
    sheet = client.open_by_url(creds_dict["spreadsheet"])
    worksheet = sheet.worksheet(sheet_name)

    # ✅ Read raw data
    raw_data = worksheet.get_all_values()

    # ✅ Extract headers from the first row
    headers = raw_data[0]  # First row is assumed to be headers

    # ✅ Ensure headers are unique (append `_1, _2` to duplicates)
    seen = {}
    unique_headers = []
    for col in headers:
        if col in seen:
            seen[col] += 1
            unique_headers.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            unique_headers.append(col)

    # ✅ Convert the data into a DataFrame
    df = pd.DataFrame(raw_data[1:], columns=unique_headers)  # Exclude first row (headers)

    return df


# Load and fetch data from Google Sheets
data1 = load_data(sheet_name="Experiments")
data2 = load_data(sheet_name="Weekly")

# st.write(data1.tail(10))


# Refresh button
if st.button("Refresh Data"):
    st.cache_data.clear()
    st.experimental_rerun()

#just feed it in directly, no need for pd.read_csv()
exp_view = data1

exp_view.dropna(axis=0, how='all', inplace=True)

# Drop columns where all cells are NaN
exp_view.dropna(axis=1, how='all', inplace=True)


st.markdown("""
<style>
.title-font {
    font-family: 'PT Sans Narrow';font-size: 30px;
    font-weight: bold;
    text-align: center;
    background-color: rgb(4,76,60);
    color: rgb(19,230,143);
    border-style: solid;
    border-width: 3px;
    border-color: rgb(19,230,143);
    border-radius: 10px;
    margin-bottom: 270px;
    
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.header1-font {
    font-family: 'PT Sans Narrow';font-size: 20px;
    font-weight: bold;
    text-align: center;
    background-color: rgb(4,76,60);
    color: rgb(19,230,143);
    border-style: solid;
    border-width: 3px;
    border-color: rgb(19,230,143);
    border-radius: 10px;
    margin-top: 40px;
    
}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="title-font">Experiments & Rollouts Dashboard</p>', unsafe_allow_html=True)
st.markdown('<p class="header1-font">Experiments</p>', unsafe_allow_html=True)


# CSS adjustments

st.markdown("""
    <style>
    .st-emotion-cache-nahz7x {
    font-family: "Source Sans Pro", sans-serif;
    margin-bottom: -20rem;
}
    </style>
    """,
unsafe_allow_html=True)


#loading in data
st.markdown("""
    <style>
.modebar{
      display: none !important;
}
</style>
    """,
unsafe_allow_html=True)


st.markdown("""
        <style>
               .block-container {
                    padding-top: 2rem;
                    padding-bottom: 0rem;
                    padding-left: 5rem;
                    padding-right: 5rem;
                }
        </style>
        """, unsafe_allow_html=True)

st.markdown("""
    <style>
            body {
                font-family: 'PT Sans Narrow';
            }
    </style>
    """, unsafe_allow_html=True)



#creating a function to calulate the remainings days left in an experiment
def rem_days(row):
    if row[9] == "Running":
        return (row[7] - datetime.today()).days
    else:
        return "None"

#converting the data types of date columns
exp_view["START DATE"] = pd.to_datetime(exp_view["START DATE"])
exp_view["END DATE"] = pd.to_datetime(exp_view["END DATE"])

#creating a year column
exp_view["YEAR"] = exp_view["START DATE"].dt.year

#creating a duration column
exp_view["DURATION"] = (exp_view["END DATE"] - exp_view["START DATE"]).dt.days

#creating the days remaining column
exp_view["DAYS REMAINING"] = exp_view.apply(rem_days, axis = 1)


stage_order = ["Running", "Completed", "Paused"]
exp_view['Sorting_Order'] = exp_view['STAGE'].apply(lambda x: stage_order.index(x))
exp_view = exp_view.sort_values(by='Sorting_Order').drop(columns=['Sorting_Order'])



#creating the graph

# Define a function to set cell background color based on the "STAGE" value
def get_fill_color(stage):
    if stage == "Completed":
        return 'rgb(4,76,60)'
    elif stage == "Running":
        return 'rgb(87,74,217)'  # Pastel blue
    elif stage == "Paused":
        return 'rgba(235,79,107,255)'  # Pastel yellow
    else:
        return 'black'  # Default color

#############
# YEAR EXPERIMNT SPLIT GRAPH

# getting the year and the month
exp_view["YEAR"] = exp_view["START DATE"].dt.year
exp_view["MONTH"] = exp_view["START DATE"].dt.month

#Building the horizontal graph for the year split
grouped_df = exp_view.groupby(["YEAR", "MONTH"]).size().reset_index(name = "Counts")

#creating a montn name that has the names of the month
grouped_df['MONTH NAME'] = grouped_df['MONTH'].apply(lambda x: calendar.month_name[x])

# Sort the DataFrame based on 'Month' to ensure the bars are in calendar order.
grouped_df.sort_values('MONTH', inplace=True)

# Prepare the data by concatenating 2022 and 2023 data with an additional categorical variable
# that indicates the year and month for the y-axis labels.
concatenated_df = pd.concat([
    grouped_df[grouped_df["YEAR"].astype(str) == "2022"].assign(YearMonth=lambda x: x["YEAR"].astype(str) + ' - ' + x["MONTH NAME"].str[:3]),
    grouped_df[grouped_df["YEAR"].astype(str) == "2023"].assign(YearMonth=lambda x: x["YEAR"].astype(str) + ' - ' + x["MONTH NAME"].str[:3]),
    grouped_df[grouped_df["YEAR"].astype(str) == "2024"].assign(YearMonth=lambda x: x["YEAR"].astype(str) + ' - ' + x["MONTH NAME"].str[:3]),
    grouped_df[grouped_df["YEAR"].astype(str) == "2025"].assign(YearMonth=lambda x: x["YEAR"].astype(str) + ' - ' + x["MONTH NAME"].str[:3])
])



# Create a list of unique city options with 'All' at the beginning
city_options = ['All'] + exp_view['CITY'].unique().tolist()

# Find the index of 'Dubai' in the city options list
default_city_index = city_options.index('Dubai') if 'Dubai' in city_options else 0


col1, col2, col3, col4 = st.columns(4)

with col1:
    city_filter = st.selectbox('City', city_options)
    metric_filter = st.selectbox('Metric', ['All'] + exp_view['PRIMARY METRIC'].unique().tolist())

with col2:
    initiative_filter = st.selectbox('Initiative', ['All'] + exp_view['INITIATIVE'].unique().tolist())
    year_filter = st.selectbox('Year', ['All'] + exp_view['YEAR'].unique().tolist())
    
with col3:
    stage_filter = st.selectbox('Stage', ['All'] + exp_view['STAGE'].unique().tolist())
    start_date_filter = st.date_input('Start Date',exp_view['START DATE'].min())

with col4:
    sub_domain_filter = st.selectbox('Sub Domain', ['All'] + exp_view['SUB DOMAIN'].unique().tolist())
    end_date_filter = st.date_input('End Date', exp_view['START DATE'].max())

# Filter the DataFrame
filtered_exp_view = exp_view.copy()


if city_filter != 'All':
    filtered_exp_view = filtered_exp_view[filtered_exp_view['CITY'] == city_filter]

if metric_filter != 'All':
    filtered_exp_view = filtered_exp_view[filtered_exp_view['PRIMARY METRIC'] == metric_filter]    

if initiative_filter != 'All':
    filtered_exp_view = filtered_exp_view[filtered_exp_view['INITIATIVE'] == initiative_filter]

if stage_filter != 'All':
    filtered_exp_view = filtered_exp_view[filtered_exp_view['STAGE'] == stage_filter]

if sub_domain_filter != 'All':
    filtered_exp_view = filtered_exp_view[filtered_exp_view['SUB DOMAIN'] == sub_domain_filter]

if year_filter != 'All':
    filtered_exp_view = filtered_exp_view[filtered_exp_view['YEAR'] == year_filter]

filtered_exp_view = filtered_exp_view[(filtered_exp_view['START DATE'] >= pd.Timestamp(start_date_filter)) & (filtered_exp_view['START DATE'] <= pd.Timestamp(end_date_filter))]
######

#############
#SUB DOMAIN SPLIT GRAPH

sub_df = pd.DataFrame(filtered_exp_view["SUB DOMAIN"].value_counts()).reset_index()
sub_df.columns = ["SUB DOMAIN", "Count"]

#############
# METRIC SPLIT GRAPH
metric_df = pd.DataFrame(filtered_exp_view["PRIMARY METRIC"].value_counts()).reset_index()
metric_df.columns = ["PRIMARY METRIC", "Count"]


# #changing the date format
# exp_view["START DATE"] = pd.to_datetime(exp_view["START DATE"])
# exp_view["END DATE"] = pd.to_datetime(exp_view["END DATE"])

filtered_exp_view["END DATE"] = filtered_exp_view["END DATE"].dt.strftime("%Y-%m-%d")
filtered_exp_view["START DATE"] = filtered_exp_view["START DATE"].dt.strftime("%Y-%m-%d")

# Create a list of fill colors based on the "STAGE" column
cell_colors = [get_fill_color(stage) for stage in filtered_exp_view["STAGE"]]

#formating all the cells, so that all the cell text can is bold
filtered_exp_view = filtered_exp_view.applymap(lambda x: f'<b>{x}</b>')

#Creating a function that will add the experiment document links to the initiative column
#There is no link, because in the new sheet that I created I didn't link the exp. docs to the sheet
def create_hyperlink(row):
    link = str(row["Experiment Doc Link"])
    link = link.replace("<b>", "")
    link = link.replace("</b>","")
    initiative_name = row["INITIATIVE"]
    return f'<a href="{link}">{initiative_name}</a>'

# Assuming you have a 'Link' column containing the URLs
filtered_exp_view["INITIATIVE"] = filtered_exp_view.apply(create_hyperlink, axis=1)

# Create the table with custom formatting
table = go.Table(
    domain=dict(x=[0, 0.495],
                y=[0, 1.0]),
    header=dict(values=["<b>INITIATIVE</b>", "<b>CITY</b>", "<b>STAGE</b>", "<b>SUB DOMAIN</b>", "<b>START DATE</b>", "<b>END DATE</b>","<b>DURATION</b>", "<b>DAYS REMAINING</b>"],
                fill_color='rgb(4,76,60)',
                align='center',
                font=dict(color='rgb(19,230,143)', size=14, family='PT Sans Narrow'),
                line_color='rgb(19,230,143)', line_width=2),
    cells=dict(values=[filtered_exp_view["INITIATIVE"], filtered_exp_view["CITY"], filtered_exp_view["STAGE"], filtered_exp_view["SUB DOMAIN"], filtered_exp_view["START DATE"], filtered_exp_view["END DATE"],filtered_exp_view["DURATION"],filtered_exp_view["DAYS REMAINING"]],
               fill_color=[['lavender' if cell_color == 'white' else cell_color for cell_color in cell_colors]],
               align='center',
               line_color='rgb(19,230,143)', line_width=2),
               cells_font=dict(color='white', size=13, family='PT Sans Narrow'),
               )


# trace1_2=go.Scatter(
#     x=[38],
#     y=[2],
#     xaxis='x1',
#     yaxis='y1',
#     mode="text",
#     name="Markers and Text",
#     text=[str(len(filtered_exp_view)) + "          <br>Total Experiments"],
#     textposition="bottom left",
#     hoverinfo='skip',
#     textfont=dict(
#         size=20,
#         family="PT Sans Narrow",
#         color='rgb(4,76,60)'
#     )
# )


trace1=go.Scatter(
    x=[1],
    y=[2],
    xaxis='x1',
    yaxis='y1',
    mode="text",
    name="Markers and Text",
    textposition="bottom center",
    hoverinfo='skip',
    textfont=dict(
        size=15,
        family="PT Sans Narrow",
        color='rgb(4,76,60)'
    )
)


trace2=go.Pie(
    labels=sub_df["SUB DOMAIN"], values=sub_df["Count"],
    marker=dict(line=dict(color='#000000', width=2)), 
    textinfo='none',
    hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>',
    domain=dict(x=[0.76, 1], y=[0.6, 0.9]))

trace2_2=go.Scatter(
    x=[1],
    y=[2],
    xaxis='x2',
    yaxis='y2',
    mode="text",
    name="Markers and Text",
    textposition="bottom center",
    hoverinfo='skip',
    textfont=dict(
        size=30,
        family="PT Sans Narrow",
        color='rgb(4,76,60)'
    )
)

trace3=go.Pie(
    labels=metric_df["PRIMARY METRIC"], values=metric_df["Count"],
    marker=dict(line=dict(color='#000000', width=2)), 
    textinfo='none',
    hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>',
    domain=dict(x=[0.53, 0.72], y=[0.075, 0.395])
    )

trace3_2=go.Scatter(
    x=[1],
    y=[2],
    xaxis='x3',
    yaxis='y3',
    mode="text",
    name="Markers and Text",
    textposition="bottom center",
    hoverinfo='skip',
    textfont=dict(
        size=30,
        family="PT Sans Narrow",
        color='rgb(4,76,60)'
    )
)

# Create a list for bar colors with the default color for all bars
bar_colors_main = ['rgba(87, 74, 216, 0.6)'] * len(concatenated_df["Counts"])

# Change the color of the last bar to a different color, e.g., red
bar_colors_main[0] = 'rgb(19,230,143)'  # Red with transparency for the last bar

# Create a list for bar colors with the default color for all bars
bar_colors_line = ['rgba(87, 74, 216, 1.0)'] * len(concatenated_df["Counts"])

# Change the color of the last bar to a different color, e.g., red
bar_colors_line[0] = 'rgb(19,230,143)'  # Red with transparency for the last bar


st.write(concatenated_df)

# trace4=go.Bar(
#     xaxis='x4',
#     yaxis='y4',
#     y=concatenated_df["YearMonth"],
#     x=concatenated_df["Counts"],
#     orientation='h',
#     hovertemplate='<b>%{label}</b><br>Count: %{value}<extra></extra>',
#     marker=dict(
#         color=bar_colors_main,  # This will set a single color for all bars
#         line=dict(color=bar_colors_line, width=3)
#     )
# )

# Ensure YEAR is stored as a string
concatenated_df["YEAR"] = concatenated_df["YEAR"].astype(str)






# trace4=go.Sunburst(
#     labels=concatenated_df["MONTH NAME"].tolist() + concatenated_df["YEAR"].unique().tolist(),  # Months as outer labels, Years as inner labels
#     parents=concatenated_df["YEAR"].tolist() + ["" for _ in concatenated_df["YEAR"].unique()],  # Months mapped to their respective years
#     values=concatenated_df["Counts"].tolist() + [concatenated_df[concatenated_df["YEAR"] == year]["Counts"].sum() for year in concatenated_df["YEAR"].unique()],  # Experiment counts
#     branchvalues="total",  # Values define the total sum per branch
#     hovertemplate="<b>%{label}</b><br>Experiments: %{value}<extra></extra>",
#     domain=dict(x=[0.76, 1], y=[0.075, 0.395])
# )


trace4=go.Sunburst(
    labels=df["YearMonth"].tolist() + df["YEAR"].astype(str).unique().tolist(),  # Labels for sunburst
    parents=df["YEAR"].astype(str).tolist() + ["" for _ in df["YEAR"].astype(str).unique()],  # Year as parent, top-level root node
    values=df["Counts"].tolist() + [df[df["YEAR"] == year]["Counts"].sum() for year in df["YEAR"].unique()],  # Experiment counts
    branchvalues="total",  # Values define the total sum per branch
    hovertemplate="<b>%{label}</b><br>Experiments: %{value}<extra></extra>",
    domain=dict(x=[0.76, 1], y=[0.075, 0.395])

    


trace4_2=go.Scatter(
    x=[1],
    y=[2],
    xaxis='x4',
    yaxis='y4',
    mode="text",
    name="Markers and Text",
    textposition="bottom center",
    hoverinfo='skip',
    textfont=dict(
        size=30,
        family="PT Sans Narrow",
        color='rgb(4,76,60)'
    )
)




layout1 = dict(
    width=1267,
    height=600,
    autosize=False,
    margin = dict(t=10),
    showlegend=False,
    xaxis1=dict(domain=[0.513, 0.743], showticklabels=False,  showgrid=False),
    xaxis2=dict(domain=[0.766, 1], showticklabels=False,  showgrid=False),
    xaxis3=dict(domain=[0.513, 0.743], showticklabels=False,  showgrid=False),
    xaxis4=dict(domain=[0.766, 1], showticklabels=False, showgrid=False), #was 0.766

    yaxis1=dict(domain=[0.55, 0.99], showticklabels=False,  showgrid=False),
    yaxis2=dict(domain=[0.55, 0.99], showticklabels=False,  showgrid=False),
    yaxis3=dict(domain=[0, 0.495], showticklabels=False, showgrid=False),
    yaxis4=dict(domain=[0, 0.495], showticklabels=False, showgrid=False), #was 0.495
    plot_bgcolor='rgb(19,230,143)'

)

fig1 = Figure(data=[table, trace1, trace2, trace2_2, trace3, trace3_2, trace4, trace4_2], layout=layout1)

fig1.update_layout(margin=dict(b=0))


#Total Experiments
fig1.add_annotation(
    x=1,
    y=4,
    text="<b>" + str(len(filtered_exp_view)) + "<br>                   Total Experiments                   </b>",
    showarrow=False,
    bordercolor='rgb(4,76,60)',  # Color of the border
    borderwidth=3,               # Width of the border
    borderpad=4,                 # Padding between the text and the border
    bgcolor='rgba(4,76,60, 0.8)',  # Background color of the box
    # xanchor='left',  # Use 'left', 'center', or 'right' for horizontal alignment
    # yanchor='bottom',  # Use 'top', 'middle', or 'bottom' for vertical alignment
    font=dict(
        size=19.5,
        family="PT Sans Narrow",
        color='rgb(19,230,143)'
    )
)

#Running Experiments
fig1.add_annotation(
    x=1,
    y=3.35,
    text="<b>" + str(len(filtered_exp_view[filtered_exp_view["STAGE"] == "<b>Running</b>"])) + "<br>                Running Experiments                </b>",
    showarrow=False,
    bordercolor='rgba(87, 74, 216, 1.0)',  # Color of the border
    borderwidth=3,               # Width of the border
    borderpad=4,                 # Padding between the text and the border
    bgcolor='rgba(87, 74, 216, 0.8)',  # Background color of the box
    # xanchor='left',  # Use 'left', 'center', or 'right' for horizontal alignment
    # yanchor='bottom',  # Use 'top', 'middle', or 'bottom' for vertical alignment
    font=dict(
        size=19.5,
        family="PT Sans Narrow",
        color='white'
    )
)

#Completed Experiments
fig1.add_annotation(
    x=1,
    y=2.7,
    text="<b>" + str(len(filtered_exp_view[filtered_exp_view["STAGE"] == "<b>Completed</b>"])) + "<br>              Completed Experiments              </b>",
    showarrow=False,
    bordercolor='rgb(4,76,60)',  # Color of the border
    borderwidth=3,               # Width of the border
    borderpad=4,                 # Padding between the text and the border
    bgcolor='rgba(4,76,60, 0.8)',  # Background color of the box
    # xanchor='left',  # Use 'left', 'center', or 'right' for horizontal alignment
    # yanchor='bottom',  # Use 'top', 'middle', or 'bottom' for vertical alignment
    font=dict(
        size=19.5,
        family="PT Sans Narrow",
        color='white'
    )
)

#Paused Experiments
fig1.add_annotation(
    x=1,
    y=2.05,
    text="<b>" + str(len(filtered_exp_view[filtered_exp_view["STAGE"] == "<b>Paused</b>"])) + "<br>                 Paused Experiments                 </b>",
    showarrow=False,
    bordercolor='rgba(235,79,107,1.0)',  # Color of the border
    borderwidth=3,               # Width of the border
    borderpad=4,                 # Padding between the text and the border
    bgcolor='rgba(235,79,107,0.8)',  # Background color of the box
    # xanchor='left',  # Use 'left', 'center', or 'right' for horizontal alignment
    # yanchor='bottom',  # Use 'top', 'middle', or 'bottom' for vertical alignment
    font=dict(
        size=19.5,
        family="PT Sans Narrow",
        color='white'
    )
)

#Year Split Title
fig1.add_annotation(
    x=10,
    y=15,
    text="<b>                        Yearly Experiment Split                        </b>",
    showarrow=False,
    bordercolor='rgba(4,76,60, 1.0)',  # Color of the border
    borderwidth=3,               # Width of the border
    borderpad=4,                 # Padding between the text and the border
    bgcolor='rgba(4,76,60, 0.8)',  # Background color of the box
    xref='x4',  # Reference to the fourth x-axis
    yref='y4',
    # xanchor='left',  # Use 'left', 'center', or 'right' for horizontal alignment
    # yanchor='bottom',  # Use 'top', 'middle', or 'bottom' for vertical alignment
    font=dict(
        size=15,
        family="PT Sans Narrow",
        color='rgb(19,230,143)'
    )
)

#Sub Domain Split Title
fig1.add_annotation(
    x=0.5,
    y=15,
    text="<b>                   Sub Domain Experiment Split                   </b>",
    showarrow=False,
    bordercolor='rgba(4,76,60, 1.0)',  # Color of the border
    borderwidth=3,               # Width of the border
    borderpad=4,                 # Padding between the text and the border
    bgcolor='rgba(4,76,60, 0.8)',  # Background color of the box
    xref='x2',  # Reference to the fourth x-axis
    yref='y2',
    # xanchor='left',  # Use 'left', 'center', or 'right' for horizontal alignment
    # yanchor='bottom',  # Use 'top', 'middle', or 'bottom' for vertical alignment
    font=dict(
        size=15,
        family="PT Sans Narrow",
        color='rgb(19,230,143)'
    )
)

#Metric Split Title
fig1.add_annotation(
    x=19.5,
    y=15,
    text="<b>                          Metric Experiment Split                       </b>",
    showarrow=False,
    bordercolor='rgba(4,76,60, 1.0)',  # Color of the border
    borderwidth=3,               # Width of the border
    borderpad=4,                 # Padding between the text and the border
    bgcolor='rgba(4,76,60, 0.8)',  # Background color of the box
    xref='x3',  # Reference to the fourth x-axis
    yref='y3',
    # xanchor='left',  # Use 'left', 'center', or 'right' for horizontal alignment
    # yanchor='bottom',  # Use 'top', 'middle', or 'bottom' for vertical alignment
    font=dict(
        size=15,
        family="PT Sans Narrow",
        color='rgb(19,230,143)'
    )
)


st.plotly_chart(fig1)

st.markdown("""
<style>
.header2-font {
    font-family: 'PT Sans Narrow';font-size: 20px;
    font-weight: bold;
    text-align: center;
    background-color: rgb(4,76,60);
    color: rgb(19,230,143);
    border-style: solid;
    border-width: 3px;
    border-color: rgb(19,230,143);
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)



st.markdown('<p class="header2-font">Rollouts</p>', unsafe_allow_html=True)

st.markdown("""
    <br>                               
""", unsafe_allow_html=True)
st.markdown("""
    <br>                               
""", unsafe_allow_html=True)


#### BI WEEKLY PLOT

#bi-weekly view sheet
weekly_data = data2

weekly_data.dropna(axis=0, how='all', inplace=True)

# Drop columns where all cells are NaN
weekly_data.dropna(axis=1, how='all', inplace=True)


#Filling in all "INITIATIVE" column with each rows' respective Initiative
# weekly_data["INITIATIVE"] = weekly_data["INITIATIVE"].fillna(method='ffill')
# weekly_data["INITIATIVE"] = weekly_data["INITIATIVE"].astype(str).replace("nan", None).fillna(method='ffill')
weekly_data["INITIATIVE"] = weekly_data["INITIATIVE"].replace("", pd.NA).fillna(method='ffill')
# weekly_data["INITIATIVE"] = weekly_data["INITIATIVE"].replace("", pd.NA).fillna(method='ffill')




#Get rid of the 4th column because we don't need it
weekly_data = weekly_data.drop(weekly_data.columns[3], axis=1)

col5, col6, col7, col8 = st.columns(4)

# Get all the unique cities
city_options = ['All'] + list(weekly_data['CITY'].unique())

# Set the default index for 'Dubai'
default_index = city_options.index('Dubai') if 'Dubai' in city_options else 0

# st.write("Columns in Weekly Data:", weekly_data.columns)


# st.write(weekly_data.head(10))


########

# Function to get filtered options for initiatives based on selected city
def get_filtered_initiatives(selected_city, data):
    if selected_city == 'All':
        # If 'All' cities are selected, return all unique initiatives without 'All'
        return sorted(data['INITIATIVE'].unique().tolist())
    else:
        # If a specific city is selected, return 'All' plus the initiatives for that city
        return ['All'] + sorted(data[data['CITY'] == selected_city]['INITIATIVE'].unique().tolist())

# Define the city options
city_options = ['All'] + sorted(weekly_data['CITY'].unique().tolist())

# Initialize the selectbox for cities
with col5:
    city_filter_2 = st.selectbox('City', city_options, index=city_options.index('Dubai') if 'Dubai' in city_options else 0)

# Initialize the selectbox for initiatives with filtered options based on the selected city
with col6:
    # Get filtered initiatives based on the selected city
    filtered_initiative_options = get_filtered_initiatives(city_filter_2, weekly_data)
    initiative_filter_2 = st.selectbox('Initiative', filtered_initiative_options)

# Now, apply the filters to the DataFrame
filtered_weekly_view = weekly_data.copy()

if city_filter_2 != 'All':
    filtered_weekly_view = filtered_weekly_view[filtered_weekly_view['CITY'] == city_filter_2]

if initiative_filter_2 != 'All':
    filtered_weekly_view = filtered_weekly_view[filtered_weekly_view['INITIATIVE'] == initiative_filter_2]

###########

st.markdown('<style>div.row-widget.stRadio > div{flex-direction:row;}</style>', unsafe_allow_html=True)


#Function to transform the data
def parse_week_dates(header_str):
    dates_str = header_str.split('\n')[-1]
    start_date, end_date = dates_str.split(' to ')
    return start_date, end_date

def transform_data(headers, row_data):
    # Extract dates from the headers skipping the first three headers as they are not dates
    headers_dates = [parse_week_dates(h) for h in headers[3:] if 'WEEK' in h]

    transformed_rows = []
    current_stage = None
    current_start_date = None
    
    # Loop through the row_data starting from the 4th element
    for i, stage in enumerate(row_data[3:], start=3):  # Start from 3 (index) to skip the first four columns
        if pd.isna(stage) and current_stage is not None:
            # Since we skip the first three elements, index should be i - 3
            transformed_rows.append({
                'Initiative-city-platform': str(row_data[0]) + '-' + str(row_data[1]) + '-' + str(row_data[2]), # Concatenate the first three columns
                'stage': current_stage,
                'start': current_start_date,
                'finish': headers_dates[i-3-1][1]  # i-3 to account for skipped columns, additional -1 for previous date
            })
            current_stage = None
        elif not pd.isna(stage):
            if current_stage is not None and current_stage != stage:
                transformed_rows.append({
                    'Initiative-city-platform': str(row_data[0]) + '-' + str(row_data[1]) + '-' + str(row_data[2]),
                    'stage': current_stage,
                    'start': current_start_date,
                    'finish': headers_dates[i-3-1][1]
                })
            if current_stage != stage:
                current_start_date = headers_dates[i-3][0]  # i-3 to account for the skipped columns
            current_stage = stage
            
    if current_stage is not None:
        transformed_rows.append({
            'Initiative-city-platform': row_data[0] + '-' + row_data[1] + '-' + row_data[2],
            'stage': current_stage,
            'start': current_start_date,
            'finish': headers_dates[-1][1]
        })
    
    return transformed_rows



# The rest of your code should remain the same.
headers = list(filtered_weekly_view.columns)


data_as_list = filtered_weekly_view.values.tolist()

# Now, you can iterate over this list and use your transform_data function
transformed_data = []
for row in data_as_list:
    transformed_rows = transform_data(headers, row)
    transformed_data.extend(transformed_rows)
######

#Putting the data in a dataframe
transformed_df = pd.DataFrame(transformed_data)

#Converring the empty strongs with nan values so empty timeslines dont appear on the Gannt Chart
transformed_df.replace("", np.nan, inplace=True)

#Calculating the height of the graph
height_number = max(len(transformed_df["Initiative-city-platform"].unique()), 1) * 30


#making sure it doesnt go below 300 height to prevent wierd lookig plots
height_number = max(height_number, 300) 


# Find the earliest date in the 'start' column
transformed_df['start'] = pd.to_datetime(transformed_df['start'])

earliest_date = transformed_df['start'].min()

# Calculate one month before the earliest date
one_month_before = earliest_date - relativedelta(months=3)


#graphing the data

#Graphingh the data in a Gantt chart
color_map = {
    'In Experiment': 'rgba(255, 255, 0, 0.8)',
    'Awaiting Results': 'rgba(87, 74, 217, 0.8)',
    'Rollout': 'rgba(0, 165, 44, 0.8)',
    'No Rollout': 'rgba(235,79,107,0.8)',
    'Paused': 'rgba(122, 123, 127, 0.8)'
}

#sorting the dataframe, because this will affect the lower code snippet when I come to creating the y-tick labels
transformed_df = transformed_df.sort_values(by='start')


fig2 = px.timeline(transformed_df, x_start="start", x_end="finish", y="Initiative-city-platform", color="stage",
                 color_discrete_map=color_map)


#get rid of the title
fig2.update_layout(title="")

#add borders to the gantt chart
fig2.update_traces(marker_line_color='black', marker_line_width=2)

fig2.update_layout(showlegend=False)
# fig2.update_traces(width=1)
fig2.update_yaxes(visible=False, showticklabels=False)

# Set the background color of the graph
fig2.update_layout(plot_bgcolor='rgb(19,230,143)')  # Or any other color you prefer

# Change the font of the tick labels on both axes and make the font bold
fig2.update_xaxes(tickfont=dict(family='PT Sans Narrow', size=12, color='white'))
fig2.update_yaxes(tickfont=dict(family='PT Sans Narrow', size=12, color='white'))

# Make the graph itself taller, we can make the height based on a number and times the pixel
fig2.update_layout(height=height_number)  # Or any other height you prefer

# Hide the legend if not needed
fig2.update_layout(showlegend=False)

fig2.update_layout(
    margin = dict(t=5)
)


# fig2.add_shape(
#     type="rect",
#     x0=-0.5,  # Adjust these coordinates to cover the area behind the y-axis
#     y0=-0.5,
#     x1=0,
#     y1=1,
#     xref="paper",
#     yref="paper",
#     fillcolor="rgb(19,230,143)",  # Set the rectangle color
#     layer="below",
#     line_width=0,
# )



# Set the x-axis to start one month before the earliest date
fig2.update_xaxes(range=[one_month_before, transformed_df['finish'].max()])


#Getting the order of the ylabel ticks

all_y_categories = []
for trace in fig2.data:
    all_y_categories.extend(trace.y)

# Remove duplicates while preserving order
unique_y_categories_ordered = list(OrderedDict.fromkeys(all_y_categories))


for i, label in enumerate(unique_y_categories_ordered):
    fig2.add_annotation(
        x=0.005,  # Adjust this value to move the annotation left or right
        y=i,
        text=label,
        showarrow=False,
        bordercolor='rgba(4,76,60, 1.0)',  # Color of the border
        borderwidth=3,               # Width of the border
        borderpad=1,                 # Padding between the text and the border
        bgcolor='rgba(4,76,60, 0.8)',  # Background color of the box
        xref="paper",
        yref="y",
        align="right",
        xanchor="left",
        yanchor="middle",
        font=dict(family='PT Sans Narrow',size=12, color='rgb(19,230,143)')
    )

# You would need to hide the original y-axis labels
fig2.update_yaxes(showticklabels=False)
fig2.update_xaxes(tickfont=dict(size=20)) 



st.plotly_chart(fig2, use_container_width=True)





# fig1.add_annotation(
#     x=19.5,
#     y=15,
#     text="<b>                                       Metric Experimnet Split                                   </b>",
#     showarrow=False,
#     bordercolor='rgba(4,76,60, 1.0)',  # Color of the border
#     borderwidth=3,               # Width of the border
#     borderpad=4,                 # Padding between the text and the border
#     bgcolor='rgba(4,76,60, 0.8)',  # Background color of the box
#     xref='x3',  # Reference to the fourth x-axis
#     yref='y3',
#     # xanchor='left',  # Use 'left', 'center', or 'right' for horizontal alignment
#     # yanchor='bottom',  # Use 'top', 'middle', or 'bottom' for vertical alignment
#     font=dict(
#         size=15,
#         family="PT Sans Narrow",
#         color='rgb(19,230,143)'
#     )
# )

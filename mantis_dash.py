import dash
import dash_auth
import dash_core_components as dcc
import dash_html_components as html
import pandas
import plotly.graph_objs as go
import plotly.express as px
import os
import statistics
import dash_daq as daq


import json

from dash.dependencies import Input, Output

import data_processors

import gunicorn
import dash_bootstrap_components as dbc

DEBUG_PRINT_ON = True

def DEBUG_PRINT(*args):
    if DEBUG_PRINT_ON:
        for arg in args:
            print(arg, end="")
        print("")

#full_string = os.getenv("VUPP")
full_string = "user:password"
split_strings = full_string.split(",")

VALID_USERNAME_PASSWORD_PAIRS = {x.split(":")[0]:x.split(":")[1] for x in split_strings}

app = dash.Dash(__name__,
    external_stylesheets=[dbc.themes.SLATE]
)

app.title = "Mantis Dashboard"
server=app.server

#auth = dash_auth.BasicAuth(
#    app,
#    VALID_USERNAME_PASSWORD_PAIRS
#)

def dash_dropdown_format(unformatted_list):
    return [{"label": x, "value": x} for x in unformatted_list]

# Getting the static variables set ----
preprocessed_data = data_processors.preprocess_data("temp_data_store")
all_df = preprocessed_data[0]
metadata = preprocessed_data[1]
session = {}
session = data_processors.set_initial_session_values(metadata, session)

# Layout
app.layout = dbc.Container([
    # Title row
    dbc.Row([
        dbc.Col(
            html.H1(
                'Mantis Dashboard',
            ), width=6),
        dbc.Col(
            html.Img(
                src=app.get_asset_url('mantis-logo.png'),
                style={
                    'overflow': 'hidden',
                    'height': 'auto',
                    'max-width': '50%',
                    'float': 'right',
                    'position': 'relative',
                },
            ), width=3)
    ], id="title row", align="center", justify="around", style={ "marginBottom": 5} ),
    # Tab select
    dbc.Tabs([
        dbc.Tab(label="Timeseries", tab_id="timeseries"),
        dbc.Tab(label="Time Overhead", tab_id="time_overhead"),
        dbc.Tab(label="GPU Time Breakdown", tab_id="time-breakdown"),
    ],
    id="tabs",
    active_tab="timeseries",
    ),
    # Contents
    html.Div(id="graph-content"),
    html.Div(id="shared_content"),
])

def get_shared_content():
    return dbc.Container([
        # Select Benchmarks row
        dbc.Row([
            dbc.Col([
                html.H4("Benchmarks:", 
                    style = {"text-align":"right"})
            ], width=6),

            dbc.Col([
                dcc.Dropdown(
                    id="benchmarks_dropdown",
                    options=dash_dropdown_format(metadata["benchmarks"]),
                    value=metadata["benchmarks"],
                    multi=True
                    ),
            ], width=6),

        ], align="center", justify="center",id='benchmark-row', style={ "marginBottom": 8} ),

        # Select Benchmark Set row (co-located applications)
        dbc.Row([
            dbc.Col([
                html.H4("Co-Located Benchmark Sets:", 
                    style = {"text-align":"right"})
            ], width=6),

            dbc.Col([
                dcc.Dropdown(
                    id="benchmark_set_dropdown",
                    options=dash_dropdown_format(metadata["benchmark_sets"]),
                    value="solo",
                    multi=True
                    ),
            ], width=6),

        ], align="center", justify="center",id='benchmark-set-row', style={ "marginBottom": 8} ),

        # Select timescale 
        dbc.Row([ dbc.Col([ html.H4("Time Handling:", style = {"text-align":"right"})
                ], width=6),
                dbc.Col([
                    dcc.RadioItems(
                        id = "time_handle_radio",
                        options = ["Absolute Time", "Percent Complete"],
                        value = "Absolute Time",
                        inline=True,
                    ),
                ], width=6),

        ], align="center", justify="center",id='timescale-row', style={ "marginBottom": 8} ),

        # Select iteration handling
        dbc.Row([
                dbc.Col([
                    html.H4("Statistical method for iterations:", 
                        style = {"text-align":"right"})
                ], width=6),

                dbc.Col([
                    dcc.Dropdown(
                        id="statistics_dropdown",
                        options=[{"label": "accumulate", "value": "accumulate"}, {"label":"average", "value": "average"}],
                        value=session["statistics"]
                        ),
                ], width=6),

        ], align="center", justify="center",id='iter-row', style={ "marginBottom": 8} ),

    ]),

# Timeseries tab layout
def timeseries_tab():
    return dbc.Container([
            # Graph row
            dbc.Row([
                dbc.Col(
                    dcc.Graph(
                        id='timeseries_graph',
                        figure={
                        'data': [
                        go.Scatter(
                                y=[], #df[session["x_axis"]],
                                x=[], #len(df[session["x_axis"]]),
                                mode='markers',
                                opacity=0.5,
                                marker={
                                'size': 15,
                                'line': {'width': 0.5, 'color': 'white'}
                                },
                                )
                        ],
                        'layout': go.Layout(
                                xaxis={'title': 'tick'},
                                )
                        }
                        ),
                    )
                    ], id='graph-row', align="center", justify="center", style={ "marginBottom": 8} ),

                    # Measurement row
                    dbc.Row([
                            dbc.Col([
                                html.H4("Metric:",
                                    style = {"text-align":"right"})
                            ], width=6),

                            dbc.Col([
                                dcc.Dropdown(
                                    id="time_measurements_dropdown",
                                    options=dash_dropdown_format(metadata["time_measurements"]),
                                    value=session["selected_time_measurements"],
                                    multi=True
                                    ),
                            ], width=6),

                    ], align="center", justify="center",id='measurement-row', style={ "marginBottom": 8} ),
                ])

def time_breakdown_tab():
    return dbc.Container([
        # Graph row
        dbc.Row([
            dbc.Col(
                dcc.Graph(
                    id='tbd-graph',
                    figure=go.Figure()
                )
            ),
        ], id='tbd-graph-row', align="center", justify="center", style={ "marginBottom": 8} ),

        # Measurement row
        dbc.Row([
            dbc.Col([
                html.H4("Metric:",
                style = {"text-align":"right"})
            ], width=6),

            dbc.Col([
                dcc.Dropdown(
                    id="tbd-measurement_dropdown",
                    options=metadata["summary_measurements"],
                    value=session["selected_gpu_summary_measurement"]
                ),
            ], width=6),

        ], align="center", justify="center", id='tbd-measurement-row', style={ "marginBottom": 8} ),

        # Extra row for selecting single benchmark
        dbc.Row([
            dbc.Col([
                html.H4("Summary Benchmark:", 
                    style = {"text-align":"right"})
            ], width=6),

            dbc.Col([
                dcc.Dropdown(
                    id="benchmark_dropdown",
                    options=dash_dropdown_format(metadata["benchmarks"]),
                    value=metadata["benchmarks"][0],
                    ),
            ], width=6),

        ], align="center", justify="center",id='benchmark-row-single', style={ "marginBottom": 8} ),

    ])   



# Time Overhead tab layout
def time_overhead_tab():
    return dbc.Container([
        # Graph row
        dbc.Row([
            dbc.Col(
                dcc.Graph(
                    id='overhead-graph',
                    figure=go.Figure()
                )
            ),
        ], id='graph-row-overhead', align="center", justify="center", style={ "marginBottom": 8} ),
    ])


# Tab switcher ----------------
@app.callback(Output("graph-content", "children"), [Input("tabs", "active_tab")])
def switch_tab(at):
    DEBUG_PRINT("in tab switcher")
    if at == "timeseries":
        return timeseries_tab()
    elif at == "time-breakdown":
        return time_breakdown_tab()
    elif at == "time_overhead":
        return time_overhead_tab()
    return html.P("This shouldn't ever be displayed...")

@app.callback(Output("shared_content", "children"), [Input("tabs", "active_tab")])
def switch_tab(at):
    DEBUG_PRINT("in tab switcher for shared content population")
    if at == "timeseries":
        return get_shared_content()
    elif at == "time-breakdown":
        return get_shared_content()
    elif at == "time_overhead":
        return get_shared_content()
    return html.P("This shouldn't ever be displayed...")

# Timeseries Tab ----------------
@app.callback(
    dash.dependencies.Output("benchmark_set_dropdown", "options"), 
    [dash.dependencies.Input("benchmarks_dropdown", "value")],)
def set_bench_dropdown(benchmarks):
    subset = ["solo"]
    for bench in benchmarks:
        for bench_set in metadata["benchmark_sets"]:
            splits = bench_set.split(":")
            if bench in splits[0]:
                subset.append(bench_set)

    return dash_dropdown_format(subset)


@app.callback(
    dash.dependencies.Output("timeseries_graph", "figure"), 
    [dash.dependencies.Input("time_measurements_dropdown", "value")],
    [dash.dependencies.Input("benchmarks_dropdown", "value")],
    [dash.dependencies.Input("benchmark_set_dropdown", "value")],
    [dash.dependencies.Input("time_handle_radio", "value")],
    [dash.dependencies.Input("statistics_dropdown", "value")],)
def set_timeseries_graph(selected_time_measurements, benchmarks, benchmark_set, time_handle, statistics):
    DEBUG_PRINT("in set graph1")
    session["selected_time_measurements"] = selected_time_measurements
    session["selected_benchmarks"] = benchmarks
    session["benchmark_set"] = benchmark_set

    session["time_handle"] = time_handle
    session["statistics"] = statistics

    tick_label = ""
    if session["time_handle"] == "Absolute Time":
        tick_label = "Time (100 ms)"
    else:
        tick_label = "Time (Pct Runtime Complete)"

    ret_list = data_processors.get_timeseries_scatter_plot(metadata, session, all_df)

    return {'data': ret_list, 'layout': go.Layout(xaxis={'title': tick_label}, yaxis={'title': "count"}, hovermode="x unified")}

# Time Breakdown Tab ---------
@app.callback(
    dash.dependencies.Output("tbd-graph", "figure"),
    [dash.dependencies.Input("tbd-measurement_dropdown", "value")],
    [dash.dependencies.Input("benchmark_dropdown", "value")],
    [dash.dependencies.Input("time_handle_radio", "value")],
    [dash.dependencies.Input("statistics_dropdown", "value")],)
def set_tbdgraph(measurement, benchmark, time_handle, statistics):
    DEBUG_PRINT("in set tbd graph")

    session["selected_gpu_summary_measurement"] = measurement
    session["selected_benchmark"] = benchmark
    session["time_handle"] = time_handle
    session["statistics"] = statistics

    tick_label = ""

    figure = data_processors.get_gpu_summary_chart(metadata, session, all_df)
    return figure

# Collector Overhead Tab ----------------
@app.callback(
    dash.dependencies.Output("overhead-graph", "figure"), 
    [dash.dependencies.Input("benchmarks_dropdown", "value")],
    [dash.dependencies.Input("benchmark_set_dropdown", "value")],
    [dash.dependencies.Input("time_handle_radio", "value")],
    [dash.dependencies.Input("statistics_dropdown", "value")],)
def set_overhead_graph(benchmarks, benchmark_set, time_handle, statistics):
    session["selected_benchmarks"] = benchmarks
    session["benchmark_set"] = benchmark_set
    session["time_handle"] = time_handle
    session["statistics"] = statistics

    tick_label = ""

    if time_handle == "Absolute Time":
        label = "Seconds"
    else:
        label = "Speedup"

    ret_list = data_processors.get_collector_time_overhead_plots(metadata, session, all_df)

    return {'data': ret_list, 'layout': go.Layout(barmode="group",xaxis={'title': tick_label}, yaxis={'title': label},)}


if __name__ == '__main__':
    app.run_server()

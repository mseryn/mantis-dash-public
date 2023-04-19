import dash
from dash import dash_table
import dash_auth
import dash_core_components as dcc
import dash_html_components as html
import pandas
import plotly.graph_objs as go
import plotly.express as px
import plotly.subplots as subplots
import os
import statistics
import math

from collections import OrderedDict

import numpy

import json

import gunicorn
import dash_bootstrap_components as dbc

DEBUG_PRINT_ON = True

def DEBUG_PRINT(*args):
    if DEBUG_PRINT_ON:
        for arg in args:
            print(arg, end="")
        print("")

def preprocess_data(path):
    DEBUG_PRINT("in preprocess data")
    df = pandas.DataFrame()
#    data = {"options": {}, "benchmarks": [], "uids": [], 
#        "types": [], "gpus":[], "measurements":set(), "all_combinations":[]}

    dataframes = []
    # Getting all dataframes from datastore
    # Note, this can digest both unsquashed CSVs and squashed Pandas pickles
    # TODO need to test if re-squashing already-squashed data hurts it, if not re-squash
    for entry in os.listdir(path):
        filename = os.path.join(path, entry)
        if ".pkl" in entry:
            dataframes.append(pandas.read_pickle(filename))
        elif ".csv" in entry:
            df = pandas.read_csv(filename)
            labels = ["collector_name", "timescale", "units", "measurements"]
            if "Unnamed: 0" in df.columns:
                labels.append("Unnamed: 0")
            modified = df.drop(labels = labels, axis = 1)
            cols = list(modified.columns)
            modified = modified.groupby(by = ["benchmark_name", "iteration"], as_index=False).first()
            dataframes.append(modified)

    # Combining all dataframes
    # Note, this makes a LOT of columns, is this an issue? TODO
    all_df = pandas.concat(dataframes, sort=False)

    # benchmark_set
    all_meas_cols = list(all_df.columns)
    all_meas_cols.remove("benchmark_name")
    all_meas_cols.remove("iteration")
    all_meas_cols.remove("duration")
    all_meas_cols.remove("benchmark_set")
    all_meas_cols.remove("collector_name")
    all_meas_cols.remove("index")
    all_meas_cols.remove("measurements")
    all_meas_cols.remove("timescale")
    all_meas_cols.remove("units")
    all_meas_cols.sort()

    all_df.replace(to_replace={'benchmark_set': numpy.nan}, value={'benchmark_set': 'solo'}, inplace=True)

    benchmarks = list(all_df["benchmark_name"].unique())
    benchmark_sets = list(all_df["benchmark_set"].unique())
    """
    fixup_benchmark_sets = []
    for benchmark_set in benchmark_sets:
        if type(benchmark_set) == str:
            if ":" not in benchmark_set:
                fixup_benchmark_sets.append(benchmark_set)
    """

    # If benchmark_set doesn't have a ":", change its value to "solo"
        
    fixup_benchmark_sets = [ benchmark_set for benchmark_set in benchmark_sets if not ':' in benchmark_set ]
    for set_name in fixup_benchmark_sets:
        all_df.replace(to_replace={'benchmark_set': set_name}, value={'benchmark_set': 'solo'}, inplace=True)
    benchmark_sets = list(all_df["benchmark_set"].unique())

    if "solo" not in benchmark_sets:
        benchmark_sets.append("solo")

    iterations = list(all_df["iteration"].unique())
    time_meas = [x for x in all_meas_cols if "summary" not in x]
    summary_meas = [x for x in all_meas_cols if "summary" in x]

    # Making color/type dict
    color_dict = {}
    option = 0
    raw_colors = px.colors.qualitative.Dark24
    # TODO this should maybe contain colors for iterations in aggregate mode idk
    for benchmark in benchmarks:
        color_dict[benchmark] = raw_colors[option]
        option += 1
        if option == 24:
            option = 0


    measurements_ordered = [x for x in time_meas]
    measurements_ordered.extend(summary_meas)
    measurements_ordered.sort()

    # Storing time overhead information both for unimpeded runtime overhead and for per-collector overhead
    bench_collector_runtime = {}
    bench_config_runtime = {}

    for benchmark in benchmarks:

        # indexed by benchmark and co-run and collector
        bench_collector_runtime[benchmark] = {}
        # indexed by benchmark and co-run
        bench_config_runtime[benchmark] = {}

        benchmark_rows_df = all_df.loc[all_df['benchmark_name'] == benchmark]

        iterations = benchmark_rows_df["iteration"].unique()
        iterations.sort()

        # TODO this does NOT handle iterations
        for iteration in iterations:
            current_data_rows = benchmark_rows_df.loc[benchmark_rows_df["iteration"] == iteration]

            for index, current_data in current_data_rows.iterrows():
                co_run_set = current_data["benchmark_set"]
                collector = current_data["collector_name"]
                duration = current_data["duration"]

                if duration != 0:
                    if co_run_set not in bench_collector_runtime[benchmark].keys():
                        bench_collector_runtime[benchmark][co_run_set] = {}

                    # For the collector overhead view, we care about all collectors
                    # Data will be [raw_duration, relative_duration]
                   # Comparison is to TTCCollector
                    bench_collector_runtime[benchmark][co_run_set][collector] = [current_data["duration"]]

                    # We only care about the TTC overhead calculation for the TTC collector
                    # Data will be [raw_duration, relative_duration]
                    # Comparison is to "solo" co_run_set
                    if collector == "TTCCollector":
                        bench_config_runtime[benchmark][co_run_set] = [current_data["duration"]]

        # Now getting relative overheads for bench collector and config runtime dicts
        if bench_config_runtime[benchmark]:
            if bench_config_runtime[benchmark]["solo"]:
                ttc_baseline = bench_config_runtime[benchmark]["solo"][0]

                for co_run_set in bench_config_runtime[benchmark].keys():
                    if "solo" not in co_run_set:
                        runtime = bench_config_runtime[benchmark][co_run_set][0]
                        overhead = ttc_baseline / runtime
                        bench_config_runtime[benchmark][co_run_set].append(overhead)
                    else:
                        bench_config_runtime[benchmark][co_run_set].append(1)
            else:
                for co_run_set in bench_config_runtime[benchmark].keys():
                    bench_config_runtime[benchmark][co_run_set].append(None)

        else:
            for co_run_set in bench_config_runtime[benchmark].keys():
                bench_config_runtime[benchmark][co_run_set].append(None)

        for co_run_set in bench_collector_runtime[benchmark].keys():
            if "TTCCollector" in list(bench_collector_runtime[benchmark][co_run_set].keys()):
                collector_baseline = bench_collector_runtime[benchmark][co_run_set]["TTCCollector"][0]

                for collector in bench_collector_runtime[benchmark][co_run_set].keys():
                    if "TTCCollector" not in collector:
                        runtime = bench_collector_runtime[benchmark][co_run_set][collector][0]
                        overhead = collector_baseline / runtime
                        bench_collector_runtime[benchmark][co_run_set][collector].append(overhead)
                    else:
                        bench_collector_runtime[benchmark][co_run_set][collector].append(1)


    metadata = {"benchmarks": benchmarks,
                "benchmark_sets": benchmark_sets,
                "iterations": iterations,
                "time_measurements": time_meas,
                "summary_measurements": summary_meas,
                "color_dict": color_dict,
                "collector_overhead": bench_collector_runtime,
                "co_run_overhead": bench_config_runtime,
                "measurements_ordered": measurements_ordered
                }


    return all_df, metadata

def order_measurements(metadata, measurements):
    return measurements

def set_initial_session_values(metadata, session):
    DEBUG_PRINT("in session set")
    if session and len(session.keys()) > 0:
        DEBUG_PRINT("session found: ", session)
        return session
    else:
        DEBUG_PRINT("session not found, initializing")
        session["selected_time_measurements"] = [metadata["time_measurements"][0]]
        session["selected_benchmarks"] = metadata["benchmarks"]
        session["selected_benchmark"] = metadata["benchmarks"][0]
        session["statistics"] = "accumulate"
        session["time_handle"] = "Absolute Time"
        session["benchmark_set"] = "solo"


        session["selected_gpu_summary_measurement"] = None
        if metadata["summary_measurements"]:
            session["selected_gpu_summary_measurement"] = metadata["summary_measurements"][0]

        DEBUG_PRINT("newly init session is: ", session)
        return session


def get_timeseries_scatter_plot(metadata, session, all_df):
    DEBUG_PRINT("in get all scatter plots")

    # This holds all the plot objects to display
    obj_list = []

    # Checking if we have data
    if len(session["selected_benchmarks"]) == 0:

        print("there is no data here")
        obj_list.append(go.Scatter( \
                        y=[], \
                        x=[], \
                        mode='markers', \
                        opacity=0.5, \
                        name="no data",
                    ))
        return obj_list

    # Making color/type dict
    color_dict = metadata["color_dict"]

    for selected_benchmark in session["selected_benchmarks"]:
        # TODO need to label for different y axes
        y_title = "NOT YET CORRECT"
        benchmark_rows_df = all_df.loc[all_df['benchmark_name'] == selected_benchmark]
        iterations = benchmark_rows_df["iteration"].unique()
        iterations.sort()

        sets = session["benchmark_set"]
        print("---")
        print("sets are")
        print(sets)
        print("---")
        data_exists = True

        for iteration in iterations:
            for measurement in session["selected_time_measurements"]:
                name = selected_benchmark + "_iteration" + str(iteration)
                current_data_rows = benchmark_rows_df.loc[benchmark_rows_df["iteration"] == iteration]

                for index, current_data in current_data_rows.iterrows():
                    if current_data["benchmark_set"] in sets or current_data["benchmark_set"] == 'solo':

                        y_data = []

                        # TODO - might need this to handle CSV file inputs
                        # CSVs reasonably don't handle comma-separated lists nicely
                        # They are wrapped in a string
                        # This is the un-wrapper
                        #if current_data[measurement].notna and not type(current_data[measurement]) == list:
                        #    print("it's not a list")
                        #    if type(list(current_data[measurement].values)[0]) == str:
                        #        print("it's a string")
                        #        current_data_string = list(current_data[measurement].values)[0]
                        #        splits = current_data_string.split("(")
                        #        for substring in splits:
                        #            substrings = substring.split(",")
                        #            if len(substrings) > 1:
                        #                value = float(substrings[1].strip("]").strip(")").strip())
                        #                y_data.append(value)

                        # Here is what happens if the data is not string-ified
                        #else:
                        #    print("it's not a string")
                        if type(current_data[measurement]) == list:
                            y_data = [x[1] for x in list(current_data[measurement])]
                        #    print(y_data)

                        length = len(y_data)

                        timeformat = ',  Time: %{x:.0f}'

                        if session["time_handle"] != "Absolute Time":
                            x_data = [int(100 * (x/length)) for x in range(0, length)]
                            timeformat = timeformat + '%'
                        else:
                            x_data = [x for x in range(0, len(y_data))]

                        if len(y_data) > 0:
                            name=current_data["benchmark_set"]
                            if name == 'solo':
                                name = selected_benchmark
                            data_exists = True
                            color = color_dict[selected_benchmark]
                            obj_list.append(go.Scatter( \
                                            y=y_data, \
                                            x=x_data, \
                                            mode='lines+markers', \
                                            opacity=0.5, \
                                            name=name, \
                                            marker_color = color, \
                                            hovertemplate=' Value: %{y:.0f}'+timeformat, \
                                        ))
        if not data_exists:
            name = "-".join([selected_benchmark, selected_uid, selected_type, selected_gpu])
            obj_list.append(go.Scatter( \
                            y=[], \
                            x=[], \
                            mode='markers', \
                            opacity=0.5, \
                            name=name,
                        ))
    return obj_list

def get_gpu_summary_chart(metadata, session, all_df):
    DEBUG_PRINT("in get time breakdown charts")

    y_label = "Percent Total Runtime (%)"

    fig = go.Figure()

    selected_benchmark = session["selected_benchmark"]
    benchmark_rows_df = all_df.loc[all_df['benchmark_name'] == selected_benchmark]
    iterations = benchmark_rows_df["iteration"].unique()
    iterations.sort()
    iteration = iterations[0]
    current_data = benchmark_rows_df.loc[benchmark_rows_df["iteration"] == iteration]
    name = selected_benchmark + "_iteration" + str(iteration)

    if not session["selected_gpu_summary_measurement"]:
        DEBUG_PRINT("No selected GPU summary measurement")
        fig.add_trace(go.Bar(
            name="",
            x=[],
            y=[],
            textposition='auto',
        ))
        fig.update_layout(
            title="Measurement",
            xaxis_title="Name",
            yaxis_title=y_label,
        )
        return fig

    current_data_strings = list(current_data[session["selected_gpu_summary_measurement"]].values)

    no_data = True

    for current in current_data_strings:
        processed_data = []
        current_iteration_data = {}
        if type(current) == str:
            current_data_string = current
                
            current_data_string = current_data_string.strip("[").strip("]")
            splits = current_data_string.split("}")
            for substring in splits:
                if substring:
                    complete_substring = substring.strip(",").strip() + "}"
                    sub_data = json.loads(complete_substring.replace("'", '"'))
                    processed_data.append(sub_data)
        if type(current) == list:
            processed_data = current
        for sub_data in processed_data:
            #if sub_data["Name"] == session["selected_gpu_summary_measurement"]:
            if "Name" in sub_data:
                percent = float(sub_data["Time (%)"])
                if percent > 0:
                    current_iteration_data[sub_data["Name"]] = percent
            elif "Operation" in sub_data:
                if "Time (%)" in sub_data:
                    percent = float(sub_data["Time (%)"])
                    if percent > 0:
                        current_iteration_data[sub_data["Operation"]] = percent
                else:
                    current_iteration_data[sub_data["Operation"]] = float(sub_data["Total (MB)"])
                    y_label = "Total Data (MB)"
                            
        if len(current_iteration_data.keys()) > 0:
            x_vals = list(current_iteration_data.keys())
            y_vals = list(current_iteration_data.values())
            no_data = False
            fig.add_trace(go.Bar(
                name=name,
                x=x_vals, 
                y=y_vals,
                text=y_vals,
                textposition='auto',
                #error_y=dict(type='data', array=errors)
            ))

    if no_data:
        DEBUG_PRINT("NO data for GPU summary chart")
        fig.add_trace(go.Bar(
            name="",
            x=[],
            y=[],
            textposition='auto',
            #error_y=dict(type='data', array=errors)
        ))

    fig.update_layout(
        title="Summary for " + session["selected_gpu_summary_measurement"],
        xaxis_title="Name",
        yaxis_title=y_label,
    )

    return fig

def get_collector_time_overhead_plots(metadata, session, all_df):
    # This holds all the plot objects to display
    obj_list = []

    # Checking if we have data
    if len(session["selected_benchmarks"]) == 0:

        print("there is no data here")
        obj_list.append(go.Scatter( \
                        y=[], \
                        x=[], \
                        mode='markers', \
                        opacity=0.5, \
                        name="no data",
                    ))
        return obj_list
    
    
    #"collector_overhead": bench_collector_runtime, \
    #"co_run_overhead": bench_config_runtime, \
    for selected_benchmark in session["selected_benchmarks"]:

        # The 0th element in the list is absolute time, the 1st element is relative speedup
        index = 0
        absolute_time = True

        if session["time_handle"] != "Absolute Time":
            absolute_time = False
            index = 1

        current_benchmark = metadata["collector_overhead"][selected_benchmark]

        for co_run_set, data in current_benchmark.items():
            names_set = []
            times_set = []
            run_name = co_run_set
            if run_name == "solo":
                run_name = selected_benchmark

            if absolute_time:
                timeformat = "%{y:.1f} s"
            else:
                timeformat = "%{y:.3f} speedup"

            for collector in data.keys():
                values = data[collector]
                if absolute_time:
                    times_set.append(values[index])
                    names_set.append(collector)

                else:
                    if len(values) > 1 and collector != "TTCCollector":
                        names_set.append(collector)
                        times_set.append(values[index])

            if len(times_set) > 1:
                obj_list.append(go.Bar( \
                                y=times_set, \
                                x=names_set, \
                                name=run_name, \
                                marker_color = metadata["color_dict"][selected_benchmark], \
                                hovertemplate= timeformat, \
                            ))
            else:
                name = run_name
                obj_list.append(go.Scatter( \
                                y=[], \
                                x=[], \
                                mode='markers', \
                                opacity=0.5, \
                                name=name,
                            ))
    return obj_list


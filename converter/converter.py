import pickle
import pandas
import os

def convert(filenames):
    dfs = []
    for filename in filenames:
        pathed = os.path.join("convert_data", filename)
        data = pandas.read_csv(pathed)
        data = squash(data)
        dfs.append(data)

    return pandas.concat(dfs, sort=False)

def squash(df):
    modified = df.drop(labels = ["Unnamed: 0", "collector_name", "timescale", "units", "measurements"], axis = 1)
    cols = list(modified.columns)
    modified = modified.groupby(by = ["benchmark_name", "iteration"], as_index=False).first()
    return modified

if __name__ == "__main__":
    filenames = ["aefoam_scaling_0.005_1node_128rank_power.csv",
        "aefoam_scaling_0.005_1node_16rank_power.csv",
        "aefoam_scaling_0.005_1node_1rank_power.csv",
        "aefoam_scaling_0.005_1node_1rank_trace.csv",
        "aefoam_scaling_0.005_1node_2rank_power.csv",
        "aefoam_scaling_0.005_1node_2rank_trace.csv",
        "aefoam_scaling_0.005_1node_32rank_power.csv",
        "aefoam_scaling_0.005_1node_4rank_power.csv",
        "aefoam_scaling_0.005_1node_4rank_trace.csv",
        "aefoam_scaling_0.005_1node_64rank_power.csv",
        "aefoam_scaling_0.005_1node_8rank_power.csv",
        "aefoam_scaling_0.005_1node_8rank_trace.csv",
        "aefoam_scaling_0.005_2node_128rank_power.csv",
        "aefoam_scaling_0.005_2node_16rank_power.csv",
        "aefoam_scaling_0.005_2node_256rank_power.csv",
        "aefoam_scaling_0.005_2node_2rank_power.csv",
        "aefoam_scaling_0.005_2node_32rank_power.csv",
        "aefoam_scaling_0.005_2node_4rank_power.csv",
        "aefoam_scaling_0.005_2node_64rank_power.csv",
        "aefoam_scaling_0.005_2node_8rank_power.csv",
        "aefoam_scaling_0.005_4node_128rank_power.csv",
        "aefoam_scaling_0.005_4node_16rank_power.csv",
        "aefoam_scaling_0.005_4node_256rank_power.csv",
        "aefoam_scaling_0.005_4node_32rank_power.csv",
        "aefoam_scaling_0.005_4node_4rank_power.csv",
        "aefoam_scaling_0.005_4node_512rank_power.csv",
        "aefoam_scaling_0.005_4node_64rank_power.csv",
        "aefoam_scaling_0.005_4node_8rank_power.csv"]
    """
    filenames = ["aefoam_fullnode_decomposed128_memory_8gpu.csv",
        "aefoam_fullnode_decomposed128_perf_0gpu.csv",
        "aefoam_fullnode_decomposed128_perf_8gpu.csv",
        "aefoam_fullnode_decomposed128_power_8gpu.csv",
        "aefoam_fullnode_decomposed16_nvidiasmi_1gpu.csv",
        "aefoam_fullnode_decomposed16_nvidiasmi_8gpu.csv",
        "aefoam_fullnode_decomposed16_perf_0gpu.csv",
        "aefoam_fullnode_decomposed16_perf_1gpu.csv",
        "aefoam_fullnode_decomposed16_perf_8gpu.csv",
        "aefoam_fullnode_decomposed2_nvidiasmi_1gpu.csv",
        "aefoam_fullnode_decomposed2_nvidiasmi_2gpu.csv",
        "aefoam_fullnode_decomposed2_perf_0gpu.csv",
        "aefoam_fullnode_decomposed2_perf_1gpu.csv",
        "aefoam_fullnode_decomposed2_perf_2gpu.csv",
        "aefoam_fullnode_decomposed32_nvidiasmi_1gpu.csv",
        "aefoam_fullnode_decomposed32_nvidiasmi_8gpu.csv",
        "aefoam_fullnode_decomposed32_perf_0gpu.csv",
        "aefoam_fullnode_decomposed32_perf_1gpu.csv",
        "aefoam_fullnode_decomposed32_perf_8gpu.csv",
        "aefoam_fullnode_decomposed4_nvidiasmi_1gpu.csv",
        "aefoam_fullnode_decomposed4_nvidiasmi_4gpu.csv",
        "aefoam_fullnode_decomposed4_perf_0gpu.csv",
        "aefoam_fullnode_decomposed4_perf_1gpu.csv",
        "aefoam_fullnode_decomposed4_perf_4gpu.csv",
        "aefoam_fullnode_decomposed64_all_8gpu.csv",
        "aefoam_fullnode_decomposed64_perf_0gpu.csv",
        "aefoam_fullnode_decomposed8_nvidiasmi_1gpu.csv",
        "aefoam_fullnode_decomposed8_nvidiasmi_8gpu.csv",
        "aefoam_fullnode_decomposed8_perf_0gpu.csv",
        "aefoam_fullnode_decomposed8_perf_1gpu.csv",
        "aefoam_fullnode_decomposed8_perf_8gpu.csv"]
    """

                
    df = convert(filenames)
    print(list(df.columns))
    #df.to_pickle("aefoam19aug22.pkl")
    df.to_pickle("aefoampowertrace.pkl")
    print(df["benchmark_name"][0])
    print(df["gpu_0_power.draw"][0])
    """
    selection = df.loc[df["benchmark_name"] == "MiniApp_1GPUs_sizeA"]
    selection = selection.loc[selection["iteration"] == 0]
    selection = selection["gpu_0_power.draw"]
    string = list(selection.array)[0]

    y_data = []
    splits = string.split("(")
    for substring in splits:
        substrings = substring.split(",")
        if len(substrings) > 1:
            value = float(substrings[1].strip("]").strip(")").strip())
            print(value)

    print(y_data)
    """


"""
['Unnamed: 0', 'benchmark_name', 'collector_name', 'iteration',
       'timescale', 'units', 'measurements', 'gpu_0_power.draw',
       'gpu_1_
"""

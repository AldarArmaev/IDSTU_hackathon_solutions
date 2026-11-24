def check(dataset):
    missing = {}
    for name, column in dataset["values"].items():
        indices = [index for index, value in enumerate(column) if value is None]
        if indices:
            missing[name] = indices

    seen = set()
    duplicates = []
    out_of_order = []
    previous = None
    for index, timestamp in enumerate(dataset["timestamps"]):
        if timestamp in seen:
            duplicates.append(index)
        if previous is not None and timestamp < previous:
            out_of_order.append(index)
        seen.add(timestamp)
        previous = timestamp

    return {
        "missing_values": missing,
        "duplicate_timestamp_indices": duplicates,
        "timestamps_out_of_order_indices": out_of_order,
    }

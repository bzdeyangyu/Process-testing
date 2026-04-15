def stub_handle(name: str, input_dict: dict) -> dict:
    return {
        "status": "stub",
        "output": f"{name} placeholder completed",
        "input_keys": sorted(input_dict.keys()),
    }

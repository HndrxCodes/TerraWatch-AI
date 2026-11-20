"""Thin wrapper around `earthaccess` (NASA Earthdata Login + CMR search + streamed reads).
Credentials come ONLY from the environment (EARTHDATA_USERNAME + EARTHDATA_PASSWORD, or EARTHDATA_TOKEN);
never hardcode them and never commit them. Not exercised by the offline unit tests."""
import time
from concurrent.futures import ThreadPoolExecutor


def login():
    import earthaccess
    try:
        auth = earthaccess.login(strategy="environment")
    except Exception as e:
        raise RuntimeError("Earthdata login failed: set EARTHDATA_USERNAME and EARTHDATA_PASSWORD "
                           "(on Kaggle: Add-ons > Secrets).") from e
    if not getattr(auth, "authenticated", False):
        raise RuntimeError("Earthdata login was not authenticated: check the credentials in the environment.")
    return earthaccess


def read_granules(concept_id, start, end, reader, workers=8, retries=3):
    """Search granules of one collection in [start, end] and apply `reader(file_like)` to each, in threads."""
    ea = login()
    results = ea.search_data(concept_id=concept_id, temporal=(start, end))
    if not results:
        raise RuntimeError(f"No granules found for {concept_id} between {start} and {end}")
    files = ea.open(results)

    def safe(f):
        for k in range(retries):
            try:
                return reader(f)
            except Exception:
                if k == retries - 1:
                    raise
                time.sleep(2 * (k + 1))

    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(safe, files))

import json
import logging
import typing as T

import boto3

from wims_feed.constants import DATES
from wims_feed.io import get_station_data, get_station_list
from wims_feed.processors import process_data
from wims_feed.settings import Settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

settings = Settings()


def run(event, context):
    """Main lambda handler"""

    S3 = boto3.client("s3")
    BASE = "https://famprod.nwcg.gov/wims/xsql"

    # Get list of stns
    stns: T.List[T.Dict[str, T.Any]] = get_station_list(settings.station_path)

    final_data = []
    for stn in stns:
        # Build request urls
        urls = [
            # Gets next seven day NFDRS16 forecast
            f"{BASE}/nfdrs.xsql?stn={stn['STNID']}&type=F&priority={stn['MP']}&fmodel=16Y&start={DATES['nfdrs']['s'].strftime('%d-%b-%y')}&end={DATES['nfdrs']['e'].strftime('%d-%b-%y')}",
            # Gets past and Day 0 NFDRS obs
            f"{BASE}/nfdrs.xsql?stn={stn['STNID']}&type=N&priority={stn['MP']}&fmodel=16Y&start={DATES['nfdrs_obs']['s'].strftime('%d-%b-%y')}&end={DATES['nfdrs_obs']['e'].strftime('%d-%b-%y')}&time={stn['RS']}",
            # Gets next seven day wx forecast
            f"{BASE}/pfcst.xsql?stn={stn['STNID']}&type=F&start={DATES['pfcst']['s'].strftime('%d-%b-%y')}&end={DATES['pfcst']['e'].strftime('%d-%b-%y')}",
            # Gets past and Day 0 wx obs
            f"{BASE}/obs.xsql?stn={stn['STNID']}&start={DATES['obs']['s'].strftime('%d-%b-%y')}&end={DATES['obs']['e'].strftime('%d-%b-%y')}&time={stn['RS']}",
        ]

        # Make requests to WIMS endpoints
        raw_data = get_station_data(urls)

        # Process only the data we need
        processed_data = process_data(raw_data, stn)
        # Add to stn list
        final_data.append(processed_data)

    # Write formatted data to txt file
    with open(f"/tmp/ndfd_predserv_fcst.json", "w") as f:
        json.dump(final_data, f)

    # Make sure to write row headers too!
    # STN_LABELS
    # Send ittttt
    with open(f"/tmp/ndfd_predserv_fcst.json", "rb") as f:
        S3.upload_fileobj(f, settings.bucket_name, "ndfd_predserv_fcst.json")

    return {"message": "WIMS data successfully written"}

import re
import time
import xml.etree.ElementTree as ET
import datetime
from urllib.request import urlopen, URLError


def url_open(url, timeout=2, n_trials=5, sleep_time=2):
    """
    Try open given url during specified timeout
    :param url: url string
    :param timeout: in seconds (e.g., 2 = 2 seconds)
    :param n_trials: number of trials
    :param sleep_time: in seconds (e.g., 2 = 2 seconds to sleep)
    :return: http.client.HTTPResponse object in case of success
    """
    latest_exception = None
    for trial in range(0, n_trials):
        try:
            response = urlopen(url, timeout=timeout)
            return response
        except URLError as e:
            latest_exception = e
            time.sleep(sleep_time)
    raise latest_exception

def get_geo_ids(start_date: datetime.date, end_date: datetime.date) -> list:
    """
    Find GSE which were published during given period.
    :param start_date: date from which you want to search gse ids (e.g., "2019/12/02")
    :param end_date: date until you want to search gse ids (e.g., "2019/12/05")
    :return: GSE ids corresponding to request
    """
    start_date_str = start_date.strftime("%Y/%m/%d")
    end_date_str = end_date.strftime("%Y/%m/%d")
    xml_url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds&term={start_date_str}:{end_date_str}[UDAT' \
              f']+AND+(gse[ETYP]+OR+gds[ETYP])&retmax=50000&usehistory=y '
    gds_ids = url_open(xml_url).read()
    gds_tree = ET.fromstring(gds_ids)
    gds_pattern = re.compile(r'^20+')
    gse_ids = list()
    for elem in gds_tree.findall('IdList/Id'):
        gse_ids.append(gds_pattern.sub('GSE', elem.text))
    return gse_ids


if __name__ == "__main__":
    ids = get_geo_ids(datetime.date(2025, 10, 1), datetime.date(2025, 10, 3))
    for geo_id in ids:
        print(f"ftp://ftp.ncbi.nlm.nih.gov/geo/series/{geo_id[:-3]}nnn/{geo_id}/soft/{geo_id}_family.soft.gz")

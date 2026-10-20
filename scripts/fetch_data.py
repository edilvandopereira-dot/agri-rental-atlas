"""Download public aggregate statistics; no company contacts or private records."""
import concurrent.futures
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://servicodados.ibge.gov.br/api/v3'
QUERIES = {
    'rental_states.json': BASE+'/agregados/9528/periodos/2022|2023|2024/variaveis/706|707?localidades=N3[all]&classificacao=12762[117725]',
    'rental_brazil.json': BASE+'/agregados/9528/periodos/2022|2023|2024/variaveis/706|707?localidades=N1[1]&classificacao=12762[117725]',
    'companies_brazil.json': BASE+'/agregados/9418/periodos/2022|2023|2024/variaveis/2585?localidades=N1[1]&classificacao=12762[117725]',
    'crop_states.json': BASE+'/agregados/1612/periodos/2022|2023|2024/variaveis/109?localidades=N3[all]&classificacao=81[2689,2696,2711,2713]',
    'crop_brazil.json': BASE+'/agregados/1612/periodos/2022|2023|2024/variaveis/109?localidades=N1[1]&classificacao=81[2689,2696,2711,2713]',
    'states.json': 'https://servicodados.ibge.gov.br/api/v1/localidades/estados',
    'brazil_states.geojson': BASE+'/malhas/paises/BR?intrarregiao=UF&qualidade=minima&formato=application/vnd.geo+json',
    'metadata_rental.json': BASE+'/agregados/9528/metadados',
    'metadata_crop.json': BASE+'/agregados/1612/metadados',
}


def fetch(item):
    filename, url = item
    request = urllib.request.Request(url, headers={'User-Agent':'EdilvandoPortfolio/1.0 public-data research'})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read()
    if payload[:2] == b'\x1f\x8b':
        payload = gzip.decompress(payload)
    data = json.loads(payload)
    if isinstance(data, dict) and 'erro' in data:
        raise ValueError(data)
    (ROOT/'data/raw'/filename).write_bytes(payload)
    return {'file': filename, 'url': url, 'sha256': hashlib.sha256(payload).hexdigest(),
            'retrieved_at': datetime.now(timezone.utc).isoformat(), 'bytes':len(payload)}


def main():
    raw = ROOT/'data/raw'
    if (raw/'manifest.json').exists():
        raise SystemExit('Snapshot already exists. Preserve/version it explicitly before refreshing.')
    raw.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        files = list(executor.map(fetch, QUERIES.items()))
    manifest = {'provider':'IBGE', 'data_years':[2022,2023,2024],
                'scope':'CEMPRE CNAE class 77.31-4, agricultural machinery rental without operator; PAM four selected crops',
                'files':files}
    (raw/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'downloaded_files':len(files), 'bytes':sum(f['bytes'] for f in files)}))


if __name__ == '__main__':
    main()

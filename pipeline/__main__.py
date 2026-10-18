import argparse
import json
from pathlib import Path
from .settings import Settings, ROOT
from .store import Store
from .runner import collect, import_jsonl
from .collectors import price_records


def main():
    parser = argparse.ArgumentParser(description='矿观采集与入库')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    sub.add_parser('status')
    sub.add_parser('bootstrap')
    crawler = sub.add_parser('collect')
    crawler.add_argument('--sources', nargs='+', choices=['mining', 'spglobal', 'disr', 'regcc', 'lme', 'mysteel', 'gfex'])
    crawler.add_argument('--days', type=int, default=30)
    crawler.add_argument('--limit', type=int, default=200)
    crawler.add_argument('--max-pages', type=int, default=250)
    importer = sub.add_parser('import-jsonl')
    importer.add_argument('path', type=Path)
    price = sub.add_parser('import-prices')
    price.add_argument('path', type=Path)
    price.add_argument('--source', required=True, choices=['LME', '上海钢联', 'GFEX'])
    price.add_argument('--url', required=True)
    args = parser.parse_args()
    store = Store(Settings())
    if args.command in ('init', 'status'):
        result = store.coverage()
    elif args.command == 'bootstrap':
        from eval.corpus import bootstrap
        result = bootstrap(store)
    elif args.command == 'collect':
        if not 1 <= args.days <= 365 or not 1 <= args.limit <= 5000 or not 1 <= args.max_pages <= 10000:
            parser.error('days 1..365, limit 1..5000, max-pages 1..10000')
        result = collect(store, args.sources, args.days, args.limit, args.max_pages)
    elif args.command == 'import-jsonl':
        result = import_jsonl(store, args.path)
    else:
        records = list(price_records(args.path.read_text(encoding='utf-8-sig'), args.source, args.url, 'json' if args.path.suffix == '.json' else 'csv'))
        result = {}
        for record in records:
            status = store.upsert(record)['status']
            result[status] = result.get(status, 0) + 1
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

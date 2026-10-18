import json
from pipeline.settings import Settings
from pipeline.store import Store
from pipeline.text import record_id, digest
from pipeline.models import utcnow
from serve.retrieval import query
from .corpus import records
from pipeline.settings import ROOT


def faithfulness(result):
    """可复现的逐项引用支持率；不是独立 LLM 裁判，不评价答案完整性。"""
    if result['abstained']:
        return None
    sources = {source['id']: source['excerpt'] for source in result['sources']}
    claims = result.get('claims', [])
    return sum(claim['text'] in sources.get(claim['source_id'], '') for claim in claims) / max(1, len(claims))


def evaluate(store, output=True):
    results = []
    benchmark = json.loads((ROOT / 'eval' / 'ground_truth.json').read_text(encoding='utf-8'))
    by_url = {record.url: record_id(record) for record in records()}
    for item in benchmark:
        gold_ids = {by_url[url] for url in item['gold_urls']}
        result = query(store, item['question'], 5)
        found = {source['id'] for source in result['sources']}
        results.append(dict(id=item['id'], question=item['question'], expected_answer=item['answer'], gold_document_ids=sorted(gold_ids),
                            retrieved_ids=sorted(found), recall_at_5=len(gold_ids & found) / len(gold_ids),
                            answer_contains_expected=item['answer'] in result['answer'],
                            faithfulness=faithfulness(result)))
    supported = [row['faithfulness'] for row in results if row['faithfulness'] is not None]
    report = dict(created_at=utcnow().isoformat(), benchmark='DISR-2023-reference-v1', corpus='10 个历史章节中文摘要；非近期三源生产质量验收',
                  benchmark_hash=digest(json.dumps(benchmark, ensure_ascii=False)), encoder=store.encoder.signature,
                  questions=len(results), recall_at_5=sum(row['recall_at_5'] for row in results) / len(results),
                  answer_accuracy=sum(row['answer_contains_expected'] for row in results) / len(results),
                  answer_faithfulness=sum(supported) / len(supported) if supported else None,
                  faithfulness_method='extractive-claim-exact-support（抽取式支持率，非独立模型判断）', results=results)
    if output:
        folder = store.settings.data_dir / 'eval'
        folder.mkdir(exist_ok=True)
        temp = folder / 'latest.tmp'
        temp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(folder / 'latest.json')
    return report


if __name__ == '__main__':
    report = evaluate(Store(Settings()))
    print(json.dumps({key: value for key, value in report.items() if key != 'results'}, ensure_ascii=False, indent=2))

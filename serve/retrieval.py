import json
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from collections import Counter
from pipeline.models import identify, MINERALS, COUNTRIES, utcnow
from pipeline.text import tokens


def infer_filters(question, explicit=None, as_of=None):
    local_zone = ZoneInfo('Asia/Shanghai')
    now = datetime.fromisoformat(as_of) if as_of else utcnow()
    now = now.replace(tzinfo=local_zone) if now.tzinfo is None else now.astimezone(local_zone)
    result = {}
    days = re.search(r'(?:近|最近|过去)\s*(\d+)\s*天', question)
    if days:
        result['since'] = (now - timedelta(days=int(days[1]))).isoformat()
    elif any(word in question for word in ('近一周', '最近一周', '近七天')):
        result['since'] = (now - timedelta(days=7)).isoformat()
    elif '本月' in question:
        result['since'] = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    elif '今天' in question or '昨天' in question:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=int('昨天' in question))
        result.update(since=start.isoformat(), until=(start + timedelta(days=1)).isoformat())
    if 'since' in result and 'until' not in result:
        result['until'] = now.isoformat()
    result['minerals'] = identify(question, MINERALS)
    result['countries'] = identify(question, COUNTRIES)
    if '政策' in question or '战略' in question:
        result['kind'] = 'policy'
    elif '价格' in question or '行情' in question:
        result['kind'] = 'price'
    elif '新闻' in question:
        result['kind'] = 'news'
    result.update({key: value for key, value in (explicit or {}).items() if value is not None})
    return result


def query(store, question, top_k=5, filters=None, as_of=None):
    applied = infer_filters(question, filters, as_of)
    clauses, args = [], []
    for key, op, column in [('kind', '=', 'd.kind'), ('since', '>=', 'd.published_at'), ('until', '<=', 'd.published_at')]:
        if applied.get(key):
            value = applied[key]
            if key in ('since', 'until'):
                value = datetime.fromisoformat(value).astimezone(timezone.utc).isoformat()
            clauses.append(f'{column}{op}?')
            args.append(value)
    for field in ('minerals', 'countries'):
        values = applied.get(field, [])
        if values:
            clauses.append('(' + ' OR '.join(f"EXISTS (SELECT 1 FROM json_each(d.payload,'$.{field}') WHERE value=?)" for _ in values) + ')')
            args.extend(values)
    where = 'WHERE ' + ' AND '.join(clauses) if clauses else ''
    vector = store.encoder.blob(question, query=True)
    with store.connect() as db:
        rows = db.execute(f'''SELECT d.id,d.payload,c.text AS passage,
            vec_distance_cosine(v.embedding,?) AS distance FROM documents d
            JOIN chunks c ON c.document_id=d.id JOIN vectors v ON v.id=c.id {where}''', [vector, *args]).fetchall()
    wanted = Counter(tokens(question))
    ranked = []
    for row in rows:
        payload = json.loads(row['payload'])
        found = Counter(tokens(payload['title'] + ' ' + row['passage']))
        lexical = sum(min(weight, found[token]) for token, weight in wanted.items()) / max(1, sum(wanted.values()))
        score = .55 * max(0, 1 - row['distance']) + .45 * lexical
        if score < .06:
            continue
        ranked.append((score, row, payload))
    ranked.sort(key=lambda item: (-item[0], item[1]['id']))
    sources, seen = [], set()
    for score, row, payload in ranked:
        if row['id'] in seen:
            continue
        seen.add(row['id'])
        sources.append(dict(id=row['id'], title=payload['title'], url=payload['url'], source=payload['source'],
                            published_at=payload['published_at'], kind=payload['kind'], is_reference=payload['is_reference'],
                            excerpt=row['passage'], score=round(score, 5)))
        if len(sources) == top_k:
            break
    claims = [{'text': source['excerpt'], 'source_id': source['id']} for source in sources]
    if not sources:
        answer = '当前数据库中没有满足这些时间、国家和矿种条件的证据，无法据此判断是否发生变化。请先采集或导入相应数据。'
    else:
        intro = '以下为库内证据；政策文件的发布不等同于政策变化，判断变化还需要前后版本对照。' if applied.get('kind') == 'policy' else '以下为数据库中的相关证据：'
        answer = intro + '\n\n' + '\n\n'.join(f"[{i}] {source['title']}（{source['published_at'][:10]} · {'历史参考中文摘要' if source['is_reference'] else '采集原文片段'}）\n{source['excerpt']}" for i, source in enumerate(sources, 1))
    return dict(answer=answer, sources=sources, claims=claims, filters=applied, abstained=not sources,
                method='extractive-hybrid', encoder=store.encoder.signature)

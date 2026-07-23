"""Flask 后端：面试题库 — 静态文件服务 + REST API

两个 JSON 文件独立读写，互不污染。
文件映射：
  cat-1 ~ cat-7  → data.json
  cat-8          → interview-1.json
"""

import json
import os
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder='.')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(BASE_DIR, 'data.json')
INTERVIEW_FILE = os.path.join(BASE_DIR, 'interview-1.json')

CATEGORY_MAP = {
    'cat-1': DATA_FILE,
    'cat-2': DATA_FILE,
    'cat-6': DATA_FILE,
    'cat-7': DATA_FILE,
    'cat-8': INTERVIEW_FILE,
    'cat-record': INTERVIEW_FILE,
}


def _load_file_for_cat(cat_id):
    """根据 cat_id 找到对应文件，返回 (file_path, categories)"""
    fp = CATEGORY_MAP.get(cat_id)
    if not fp or not os.path.exists(fp):
        return None, None
    with open(fp, 'r', encoding='utf-8') as f:
        return fp, json.load(f)


def _save_file(file_path, categories):
    """写回指定文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)


def _get_questions(cat, subcat_id=None):
    """获取题目数组：有 subcat_id 时返回子分组内的，否则返回 category 的"""
    if subcat_id:
        for sc in cat.get('subcategories', []):
            if sc['id'] == subcat_id:
                return sc['questions']
        return None
    return cat.get('questions', [])


# ── 静态文件 ──

@app.route('/')
def index():
    return send_from_directory(BASE_DIR, '面试题库_完整合并版.html')


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(BASE_DIR, filename)


# ── API: 获取全量数据 ──

@app.route('/api/data')
def api_get_data():
    seen = {}
    for fp, order in [(DATA_FILE, 0), (INTERVIEW_FILE, 1)]:
        if os.path.exists(fp):
            with open(fp, 'r', encoding='utf-8') as f:
                for cat in json.load(f):
                    cid = cat['id']
                    correct_file = CATEGORY_MAP.get(cid)
                    is_correct = fp == correct_file
                    if cid in seen:
                        if is_correct:
                            seen[cid] = cat
                    else:
                        seen[cid] = cat
    return jsonify(list(seen.values()))


# ── API: 新增题目 ──

@app.route('/api/questions/<cat_id>', methods=['POST'])
def api_add_question(cat_id):
    body = request.get_json(force=True)
    title = body.get('title', '').strip()
    answer = body.get('answer', '').strip()
    subcat_id = body.get('subcat_id')
    if not title or not answer:
        return jsonify({'error': '标题和答案不能为空'}), 400

    fp, cats = _load_file_for_cat(cat_id)
    if not fp:
        return jsonify({'error': f'Category not found: {cat_id}'}), 404

    cat = next((c for c in cats if c['id'] == cat_id), None)
    if not cat:
        return jsonify({'error': f'Category not found: {cat_id}'}), 404

    questions = _get_questions(cat, subcat_id)
    if questions is None:
        return jsonify({'error': f'Subcategory not found: {subcat_id}'}), 404

    max_num = max((q['num'] for q in questions), default=0)
    new_q = {'num': max_num + 1, 'title': title, 'answer': answer}
    questions.append(new_q)
    _save_file(fp, cats)
    return jsonify(new_q), 201


# ── API: 修改题目 ──

@app.route('/api/questions/<cat_id>/<int:num>', methods=['PUT'])
def api_update_question(cat_id, num):
    body = request.get_json(force=True)
    title = body.get('title', '').strip()
    answer = body.get('answer', '').strip()
    subcat_id = body.get('subcat_id')
    if not title or not answer:
        return jsonify({'error': '标题和答案不能为空'}), 400

    fp, cats = _load_file_for_cat(cat_id)
    if not fp:
        return jsonify({'error': f'Category not found: {cat_id}'}), 404

    cat = next((c for c in cats if c['id'] == cat_id), None)
    if not cat:
        return jsonify({'error': f'Category not found: {cat_id}'}), 404

    questions = _get_questions(cat, subcat_id)
    if questions is None:
        return jsonify({'error': f'Subcategory not found: {subcat_id}'}), 404

    q = next((q for q in questions if q['num'] == num), None)
    if not q:
        return jsonify({'error': f'Question {num} not found'}), 404

    q['title'] = title
    q['answer'] = answer
    _save_file(fp, cats)
    return jsonify(q)


# ── API: 删除题目 ──

@app.route('/api/questions/<cat_id>/<int:num>', methods=['DELETE'])
def api_delete_question(cat_id, num):
    body = request.get_json(force=True)
    subcat_id = body.get('subcat_id') if body else None

    fp, cats = _load_file_for_cat(cat_id)
    if not fp:
        return jsonify({'error': f'Category not found: {cat_id}'}), 404

    cat = next((c for c in cats if c['id'] == cat_id), None)
    if not cat:
        return jsonify({'error': f'Category not found: {cat_id}'}), 404

    questions = _get_questions(cat, subcat_id)
    if questions is None:
        return jsonify({'error': f'Subcategory not found: {subcat_id}'}), 404

    before = len(questions)
    cat_questions = questions[:]  # work on copy for removal
    questions.clear()
    for q in cat_questions:
        if q['num'] != num:
            questions.append(q)

    if len(questions) == before:
        # re-check if anything was actually removed
        pass

    _save_file(fp, cats)
    return jsonify({'success': True})


# ── API: 重排序 ──

@app.route('/api/reorder/<cat_id>', methods=['PUT'])
def api_reorder(cat_id):
    body = request.get_json(force=True)
    questions = body.get('questions', [])
    subcat_id = body.get('subcat_id')
    if not questions:
        return jsonify({'error': 'questions 数组不能为空'}), 400

    fp, cats = _load_file_for_cat(cat_id)
    if not fp:
        return jsonify({'error': f'Category not found: {cat_id}'}), 404

    cat = next((c for c in cats if c['id'] == cat_id), None)
    if not cat:
        return jsonify({'error': f'Category not found: {cat_id}'}), 404

    target = _get_questions(cat, subcat_id)
    if target is None:
        return jsonify({'error': f'Subcategory not found: {subcat_id}'}), 404

    # 重新编号
    for i, q in enumerate(questions):
        q['num'] = i + 1

    target.clear()
    target.extend(questions)
    _save_file(fp, cats)
    return jsonify({'success': True})


# ── API: 子分组 CRUD ──

@app.route('/api/subcategories/<cat_id>', methods=['POST'])
def api_add_subcategory(cat_id):
    body = request.get_json(force=True)
    title = body.get('title', '').strip()
    icon = body.get('icon', '📁').strip()
    if not title:
        return jsonify({'error': '子分组标题不能为空'}), 400

    fp, cats = _load_file_for_cat(cat_id)
    if not fp:
        return jsonify({'error': f'Category not found: {cat_id}'}), 404

    cat = next((c for c in cats if c['id'] == cat_id), None)
    if not cat:
        return jsonify({'error': f'Category not found: {cat_id}'}), 404

    if 'subcategories' not in cat:
        cat['subcategories'] = []

    existing_ids = {sc['id'] for sc in cat['subcategories']}
    base_id = 'group'
    n = 1
    sc_id = f'{base_id}-{n}'
    while sc_id in existing_ids:
        n += 1
        sc_id = f'{base_id}-{n}'

    new_sc = {
        'id': sc_id,
        'title': title,
        'icon': icon,
        'questions': [],
    }
    cat['subcategories'].append(new_sc)
    _save_file(fp, cats)
    return jsonify(new_sc), 201


@app.route('/api/subcategories/<cat_id>/<subcat_id>', methods=['PUT'])
def api_update_subcategory(cat_id, subcat_id):
    body = request.get_json(force=True)
    title = body.get('title', '').strip()
    icon = body.get('icon', '').strip()

    fp, cats = _load_file_for_cat(cat_id)
    if not fp:
        return jsonify({'error': f'Category not found: {cat_id}'}), 404

    cat = next((c for c in cats if c['id'] == cat_id), None)
    if not cat:
        return jsonify({'error': f'Category not found: {cat_id}'}), 404

    sc = next((s for s in cat.get('subcategories', []) if s['id'] == subcat_id), None)
    if not sc:
        return jsonify({'error': f'Subcategory not found: {subcat_id}'}), 404

    if title:
        sc['title'] = title
    if icon:
        sc['icon'] = icon
    _save_file(fp, cats)
    return jsonify(sc)


@app.route('/api/subcategories/<cat_id>/<subcat_id>', methods=['DELETE'])
def api_delete_subcategory(cat_id, subcat_id):
    fp, cats = _load_file_for_cat(cat_id)
    if not fp:
        return jsonify({'error': f'Category not found: {cat_id}'}), 404

    cat = next((c for c in cats if c['id'] == cat_id), None)
    if not cat:
        return jsonify({'error': f'Category not found: {cat_id}'}), 404

    before = len(cat.get('subcategories', []))
    cat['subcategories'] = [s for s in cat.get('subcategories', []) if s['id'] != subcat_id]
    if len(cat['subcategories']) == before:
        return jsonify({'error': f'Subcategory not found: {subcat_id}'}), 404

    _save_file(fp, cats)
    return jsonify({'success': True})


if __name__ == '__main__':
    print(' * 启动面试题库服务器 → http://localhost:8082')
    app.run(host='0.0.0.0', port=8082, debug=True)

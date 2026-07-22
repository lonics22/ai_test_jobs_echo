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
    'cat-3': DATA_FILE,
    'cat-4': DATA_FILE,
    'cat-5': DATA_FILE,
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


# ── 静态文件 ──

@app.route('/')
def index():
    return send_from_directory(BASE_DIR, '面试题库_完整合并版.html')


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(BASE_DIR, filename)


# ── API: 获取全量数据（合并两个文件供前端展示） ──

@app.route('/api/data')
def api_get_data():
    """合并两个文件。重复 cat_id 时用正确文件中的版本覆盖（防御性）"""
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
    if not title or not answer:
        return jsonify({'error': '标题和答案不能为空'}), 400

    fp, cats = _load_file_for_cat(cat_id)
    if not fp:
        return jsonify({'error': f'Category not found: {cat_id}'}), 404

    cat = next((c for c in cats if c['id'] == cat_id), None)
    if not cat:
        return jsonify({'error': f'Category not found: {cat_id}'}), 404

    max_num = max((q['num'] for q in cat['questions']), default=0)
    new_q = {
        'num': max_num + 1,
        'title': title,
        'answer': answer,
    }
    cat['questions'].append(new_q)
    _save_file(fp, cats)
    return jsonify(new_q), 201


# ── API: 修改题目 ──

@app.route('/api/questions/<cat_id>/<int:num>', methods=['PUT'])
def api_update_question(cat_id, num):
    body = request.get_json(force=True)
    title = body.get('title', '').strip()
    answer = body.get('answer', '').strip()
    if not title or not answer:
        return jsonify({'error': '标题和答案不能为空'}), 400

    fp, cats = _load_file_for_cat(cat_id)
    if not fp:
        return jsonify({'error': f'Category not found: {cat_id}'}), 404

    cat = next((c for c in cats if c['id'] == cat_id), None)
    if not cat:
        return jsonify({'error': f'Category not found: {cat_id}'}), 404

    q = next((q for q in cat['questions'] if q['num'] == num), None)
    if not q:
        return jsonify({'error': f'Question {num} not found'}), 404

    q['title'] = title
    q['answer'] = answer
    _save_file(fp, cats)
    return jsonify(q)


# ── API: 删除题目 ──

@app.route('/api/questions/<cat_id>/<int:num>', methods=['DELETE'])
def api_delete_question(cat_id, num):
    fp, cats = _load_file_for_cat(cat_id)
    if not fp:
        return jsonify({'error': f'Category not found: {cat_id}'}), 404

    cat = next((c for c in cats if c['id'] == cat_id), None)
    if not cat:
        return jsonify({'error': f'Category not found: {cat_id}'}), 404

    before = len(cat['questions'])
    cat['questions'] = [q for q in cat['questions'] if q['num'] != num]
    if len(cat['questions']) == before:
        return jsonify({'error': f'Question {num} not found'}), 404

    _save_file(fp, cats)
    return jsonify({'success': True})


# ── API: 重排序 ──

@app.route('/api/reorder/<cat_id>', methods=['PUT'])
def api_reorder(cat_id):
    body = request.get_json(force=True)
    questions = body.get('questions', [])
    if not questions:
        return jsonify({'error': 'questions 数组不能为空'}), 400

    fp, cats = _load_file_for_cat(cat_id)
    if not fp:
        return jsonify({'error': f'Category not found: {cat_id}'}), 404

    cat = next((c for c in cats if c['id'] == cat_id), None)
    if not cat:
        return jsonify({'error': f'Category not found: {cat_id}'}), 404

    # 重新编号
    for i, q in enumerate(questions):
        q['num'] = i + 1

    cat['questions'] = questions
    _save_file(fp, cats)
    return jsonify({'success': True})


if __name__ == '__main__':
    print(' * 启动面试题库服务器 → http://localhost:8082')
    app.run(host='0.0.0.0', port=8082, debug=True)

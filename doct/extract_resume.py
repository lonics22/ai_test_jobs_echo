import docx2txt, os

# Find the resume file
target = 'D:/面试/AI_test_jobs/简历/非交易所修改'
for f in os.listdir(target):
    if f.endswith('.docx') and not f.startswith('~$'):
        path = os.path.join(target, f)
        text = docx2txt.process(path)
        out_path = 'D:/面试/AI_test_jobs/doct/resume_text.txt'
        with open(out_path, 'w', encoding='utf-8') as out:
            out.write(text)
        print(f"Extracted: {f} -> {out_path}")
        print(f"Length: {len(text)} chars")
        break

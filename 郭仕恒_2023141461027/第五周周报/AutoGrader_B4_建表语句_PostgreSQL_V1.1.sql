-- AutoGrader 项目（Beta）B4 模块建表语句 PostgreSQL V1.1
-- 技术栈：Python 3.10+ / FastAPI / PostgreSQL / JWT
-- 说明：本脚本面向 PostgreSQL 13+，可直接用于原型开发与后续扩展。

BEGIN;

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    real_name VARCHAR(50),
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'teacher', 'student', 'service')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS classes (
    id BIGSERIAL PRIMARY KEY,
    class_name VARCHAR(100) NOT NULL,
    grade VARCHAR(30),
    term VARCHAR(30),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS students (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE,
    class_id BIGINT NOT NULL,
    student_no VARCHAR(30) NOT NULL UNIQUE,
    name VARCHAR(50) NOT NULL,
    email VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'normal' CHECK (status IN ('normal', 'disabled', 'graduated')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_students_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_students_class FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS problems (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    difficulty VARCHAR(20) NOT NULL DEFAULT 'medium' CHECK (difficulty IN ('easy', 'medium', 'hard')),
    time_limit_ms INTEGER NOT NULL DEFAULT 1000,
    memory_limit_mb INTEGER NOT NULL DEFAULT 128,
    testcase_version INTEGER NOT NULL DEFAULT 1,
    created_by BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_problems_creator FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS problem_testcases (
    id BIGSERIAL PRIMARY KEY,
    problem_id BIGINT NOT NULL,
    case_no INTEGER NOT NULL,
    input_data TEXT NOT NULL,
    expected_output TEXT NOT NULL,
    is_sample BOOLEAN NOT NULL DEFAULT FALSE,
    is_hidden BOOLEAN NOT NULL DEFAULT TRUE,
    score_weight NUMERIC(5,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_problem_testcases_problem_case UNIQUE (problem_id, case_no),
    CONSTRAINT fk_problem_testcases_problem FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS assignments (
    id BIGSERIAL PRIMARY KEY,
    problem_id BIGINT NOT NULL,
    class_id BIGINT NOT NULL,
    title VARCHAR(200) NOT NULL,
    start_time TIMESTAMPTZ,
    deadline TIMESTAMPTZ NOT NULL,
    max_submit_count INTEGER NOT NULL DEFAULT 20,
    status VARCHAR(20) NOT NULL DEFAULT 'published' CHECK (status IN ('draft', 'published', 'closed')),
    created_by BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_assignments_problem FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE RESTRICT,
    CONSTRAINT fk_assignments_class FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE RESTRICT,
    CONSTRAINT fk_assignments_creator FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS submissions (
    id BIGSERIAL PRIMARY KEY,
    assignment_id BIGINT NOT NULL,
    problem_id BIGINT NOT NULL,
    student_id BIGINT NOT NULL,
    language VARCHAR(30) NOT NULL,
    code TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'judging', 'finished', 'failed')),
    submit_count INTEGER NOT NULL DEFAULT 1,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_submissions_assignment FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
    CONSTRAINT fk_submissions_problem FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE RESTRICT,
    CONSTRAINT fk_submissions_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS judge_tasks (
    id BIGSERIAL PRIMARY KEY,
    submission_id BIGINT NOT NULL UNIQUE,
    task_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (task_status IN ('pending', 'fetched', 'judging', 'finished', 'failed')),
    fetch_count INTEGER NOT NULL DEFAULT 0,
    last_fetched_at TIMESTAMPTZ,
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_judge_tasks_submission FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS judge_results (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL,
    submission_id BIGINT NOT NULL UNIQUE,
    score NUMERIC(5,2) NOT NULL DEFAULT 0,
    runtime_ms INTEGER,
    memory_kb INTEGER,
    passed_count INTEGER NOT NULL DEFAULT 0,
    total_count INTEGER NOT NULL DEFAULT 0,
    result_detail JSONB,
    judged_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_judge_results_task FOREIGN KEY (task_id) REFERENCES judge_tasks(id) ON DELETE CASCADE,
    CONSTRAINT fk_judge_results_submission FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS scores (
    id BIGSERIAL PRIMARY KEY,
    assignment_id BIGINT NOT NULL,
    student_id BIGINT NOT NULL,
    submission_id BIGINT,
    final_score NUMERIC(5,2) NOT NULL DEFAULT 0,
    judge_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (judge_status IN ('pending', 'judging', 'finished', 'failed')),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_scores_assignment_student UNIQUE (assignment_id, student_id),
    CONSTRAINT fk_scores_assignment FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
    CONSTRAINT fk_scores_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    CONSTRAINT fk_scores_submission FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS knowledge_tags (
    id BIGSERIAL PRIMARY KEY,
    tag_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS problem_knowledge_tags (
    id BIGSERIAL PRIMARY KEY,
    problem_id BIGINT NOT NULL,
    tag_id BIGINT NOT NULL,
    CONSTRAINT uq_problem_tag UNIQUE (problem_id, tag_id),
    CONSTRAINT fk_problem_tags_problem FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE,
    CONSTRAINT fk_problem_tags_tag FOREIGN KEY (tag_id) REFERENCES knowledge_tags(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS student_knowledge_profile (
    id BIGSERIAL PRIMARY KEY,
    student_id BIGINT NOT NULL,
    tag_id BIGINT NOT NULL,
    wrong_count INTEGER NOT NULL DEFAULT 0,
    profile_score NUMERIC(5,2) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_student_tag UNIQUE (student_id, tag_id),
    CONSTRAINT fk_student_profile_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    CONSTRAINT fk_student_profile_tag FOREIGN KEY (tag_id) REFERENCES knowledge_tags(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_students_class_id ON students(class_id);
CREATE INDEX IF NOT EXISTS idx_problem_testcases_problem_id ON problem_testcases(problem_id);
CREATE INDEX IF NOT EXISTS idx_problem_testcases_problem_sample ON problem_testcases(problem_id, is_sample);
CREATE INDEX IF NOT EXISTS idx_assignments_class_id ON assignments(class_id);
CREATE INDEX IF NOT EXISTS idx_submissions_student_id ON submissions(student_id);
CREATE INDEX IF NOT EXISTS idx_submissions_assignment_id ON submissions(assignment_id);
CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status);
CREATE INDEX IF NOT EXISTS idx_judge_tasks_status ON judge_tasks(task_status);
CREATE INDEX IF NOT EXISTS idx_scores_assignment_id ON scores(assignment_id);
CREATE INDEX IF NOT EXISTS idx_scores_student_id ON scores(student_id);
CREATE INDEX IF NOT EXISTS idx_problem_knowledge_tags_problem_id ON problem_knowledge_tags(problem_id);
CREATE INDEX IF NOT EXISTS idx_student_knowledge_profile_student_id ON student_knowledge_profile(student_id);

COMMIT;

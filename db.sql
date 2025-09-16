CREATE TABLE IF NOT EXISTS audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action VARCHAR(255) NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE DATABASE IF NOT EXISTS exam_auth;
USE exam_auth;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    face_image VARCHAR(255)
);


CREATE TABLE IF NOT EXISTS exam_questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question_text TEXT NOT NULL,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS answers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    question_id INT NOT NULL,
    answer_text TEXT NOT NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finalized BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (student_id) REFERENCES users(id),
    FOREIGN KEY (question_id) REFERENCES exam_questions(id)
);
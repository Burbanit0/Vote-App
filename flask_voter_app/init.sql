-- init.sql
DROP DATABASE IF EXISTS mydatabase;
CREATE DATABASE mydatabase;

\c mydatabase

-- Create your tables and insert seed data here
CREATE TABLE candidates (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50)
);

CREATE TABLE voters (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50)
);

CREATE TABLE votes (
    id SERIAL PRIMARY KEY,
    voter_id INTEGER REFERENCES voters(id),
    candidate_id INTEGER REFERENCES candidates(id),
    vote_type VARCHAR(50),
    rank INTEGER
);

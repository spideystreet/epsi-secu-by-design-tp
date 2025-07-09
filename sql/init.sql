-- Initialize testvault database with livre table
USE testvault;

-- Create livre table with id and titre columns
CREATE TABLE IF NOT EXISTS livre (
    id INT AUTO_INCREMENT PRIMARY KEY,
    titre VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data for testing
INSERT INTO livre (titre) VALUES 
    ('Le Petit Prince'),
    ('1984'),
    ('Les Misérables'),
    ('Le Seigneur des Anneaux'),
    ('Harry Potter à l\'école des sorciers');

-- Grant privileges to testvault user
GRANT SELECT, INSERT, UPDATE, DELETE ON testvault.* TO 'testvault'@'%';
FLUSH PRIVILEGES; 
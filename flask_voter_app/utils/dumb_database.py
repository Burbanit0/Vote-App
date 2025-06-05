import os
import subprocess

# Database configuration
DATABASE_URI = 'postgresql://yourusername:yourpassword@yourhost/yourdbname'
BACKUP_DIR = '/path/to/backup/directory'


# Create a backup of the database
def backup_database(backup_dir=BACKUP_DIR, db_uri=DATABASE_URI):
    # Ensure the backup directory exists
    os.makedirs(backup_dir, exist_ok=True)

    # Create a backup file path
    backup_file = os.path.join(backup_dir, 'database_backup.dump')

    # Create the pg_dump command
    command = [
        'pg_dump',
        '-U', 'yourusername',
        '-h', 'yourhost',
        '-F', 'c',
        '-b',
        '-v',
        '-f', backup_file,
        'yourdbname'
    ]

    # Execute the pg_dump command
    result = subprocess.run(command, capture_output=True, text=True)

    # Check for errors
    if result.returncode != 0:
        print(f"Error during backup: {result.stderr}")
    else:
        print(f"Backup completed successfully: {backup_file}")


# Example usage
backup_database()

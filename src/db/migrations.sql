BEGIN;

    -- Put all your migrations commands here.
    -- It is HIGHLY recommended to use EXISTS guards to not
    -- accidentally apply migrations more than once.

    INSERT INTO serversettings (name, value)
    SELECT 'Server Announcement Channel', '0'
    WHERE NOT EXISTS (
        SELECT * FROM serversettings
        WHERE name='Server Announcement Channel'
    );

    INSERT INTO roles (name, value)
    SELECT 'Yapper', '0'
    WHERE NOT EXISTS (
        SELECT * FROM roles
        WHERE name='Yapper'
    );

    ALTER TABLE users ADD COLUMN IF NOT EXISTS monthly_points int NOT NULL DEFAULT 0;

    CREATE TABLE IF NOT EXISTS parameters (
        parameter_name VARCHAR(255) NOT NULL,
        parameter_value VARCHAR(255)
    );
    INSERT INTO parameters (parameter_name, parameter_value)
    SELECT 'monthly_yapper', '0'
    WHERE NOT EXISTS (
        SELECT * FROM parameters
        WHERE parameter_name='monthly_yapper'
    );

    INSERT INTO parameters (parameter_name, parameter_value)
    SELECT 'verification_enabled', '1'
    WHERE NOT EXISTS (
        SELECT * FROM parameters
        WHERE parameter_name='verification_enabled'
    );

COMMIT;

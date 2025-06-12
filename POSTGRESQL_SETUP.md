
# PostgreSQL Setup Guide

This guide helps you set up PostgreSQL for your inventory management system.

## Option 1: Using Replit's PostgreSQL Database

1. Open a new tab in Replit and type "Database"
2. In the "Database" panel, click "create a database"
3. This will automatically set up a PostgreSQL database and add the `DATABASE_URL` to your environment variables
4. The `DATABASE_URL` will be automatically configured in your Replit environment

## Option 2: Manual PostgreSQL Setup

If you're running this locally or want to use a custom PostgreSQL instance:

### 1. Update your .env file

Replace the `DATABASE_URL` in your `.env` file with your PostgreSQL connection string:

```
DATABASE_URL=postgresql://username:password@host:port/database_name
```

Example:
```
DATABASE_URL=postgresql://myuser:mypassword@localhost:5432/inventory_management
```

### 2. Create the Database

Connect to PostgreSQL and create the database:

```sql
CREATE DATABASE inventory_management;
```

### 3. Initialize the Database Schema

Run the initialization script:

```bash
python init_postgres.py
```

## Database URL Format

The DATABASE_URL should follow this format:
```
postgresql://[username]:[password]@[host]:[port]/[database_name]
```

Where:
- `username`: Your PostgreSQL username
- `password`: Your PostgreSQL password  
- `host`: Database host (usually `localhost` for local development)
- `port`: Database port (usually `5432` for PostgreSQL)
- `database_name`: Name of your database (e.g., `inventory_management`)

## Connection Pooling (Optional)

For better performance in production, you can use connection pooling by modifying the DATABASE_URL:

```
DATABASE_URL=postgresql://username:password@host-pooler:port/database_name
```

## Troubleshooting

### Common Issues:

1. **Connection refused**: Make sure PostgreSQL is running
2. **Authentication failed**: Check username and password
3. **Database does not exist**: Create the database first
4. **Permission denied**: Ensure the user has proper permissions

### Testing the Connection:

You can test your database connection by running:

```bash
python init_postgres.py
```

This will verify the connection and set up the required tables.

## Environment Variables

After setting up PostgreSQL, make sure these environment variables are configured:

```
DATABASE_URL=postgresql://username:password@host:port/database_name
```

The application will automatically use PostgreSQL instead of SQLite when this is configured.

-- ============================================================
-- DataAisle — Database Schema
-- File    : 001_dataaisle_schema.sql
-- Run in  : SQL Server Express 2022 via SSMS
-- ============================================================

-- ------------------------------------------------------------
-- 0. Create the database
-- ------------------------------------------------------------
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'DataAisle')
BEGIN
    CREATE DATABASE DataAisle;
END
GO

USE DataAisle;
GO

-- ============================================================
-- DIMENSION TABLES
-- ============================================================

-- ------------------------------------------------------------
-- dim_date
-- Pre-populated via a Python date-spine generator (see Phase 2)
-- ------------------------------------------------------------
IF OBJECT_ID('dbo.dim_date', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.dim_date (
        date_id     INT             NOT NULL PRIMARY KEY,   -- surrogate: YYYYMMDD
        full_date   DATE            NOT NULL,
        day         TINYINT         NOT NULL,
        month       TINYINT         NOT NULL,
        quarter     TINYINT         NOT NULL,
        year        SMALLINT        NOT NULL,
        day_name    VARCHAR(10)     NOT NULL,               -- 'Monday', 'Tuesday' ...
        month_name  VARCHAR(10)     NOT NULL,               -- 'January', 'February' ...
        is_weekend  BIT             NOT NULL DEFAULT 0
    );
END
GO

-- ------------------------------------------------------------
-- dim_product
-- ------------------------------------------------------------
IF OBJECT_ID('dbo.dim_product', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.dim_product (
        product_id      INT             NOT NULL IDENTITY(1,1) PRIMARY KEY,
        sku             VARCHAR(50)     NOT NULL UNIQUE,
        name            VARCHAR(150)    NOT NULL,
        category        VARCHAR(80)     NOT NULL,
        brand           VARCHAR(80)     NOT NULL,
        created_at      DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME()
    );
END
GO

-- ------------------------------------------------------------
-- dim_store
-- ------------------------------------------------------------
IF OBJECT_ID('dbo.dim_store', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.dim_store (
        store_id    INT             NOT NULL IDENTITY(1,1) PRIMARY KEY,
        name        VARCHAR(120)    NOT NULL,
        city        VARCHAR(80)     NOT NULL,
        region      VARCHAR(80)     NOT NULL,
        country     VARCHAR(80)     NOT NULL DEFAULT 'Canada',
        created_at  DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME()
    );
END
GO

-- ------------------------------------------------------------
-- dim_supplier
-- ------------------------------------------------------------
IF OBJECT_ID('dbo.dim_supplier', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.dim_supplier (
        supplier_id     INT             NOT NULL IDENTITY(1,1) PRIMARY KEY,
        name            VARCHAR(120)    NOT NULL,
        country         VARCHAR(80)     NOT NULL,
        contact_email   VARCHAR(120)    NULL,
        created_at      DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME()
    );
END
GO

-- ============================================================
-- FACT TABLE
-- ============================================================

-- ------------------------------------------------------------
-- fact_sales  (central fact — star schema core)
-- ------------------------------------------------------------
IF OBJECT_ID('dbo.fact_sales', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.fact_sales (
        sale_id         BIGINT          NOT NULL IDENTITY(1,1) PRIMARY KEY,
        date_id         INT             NOT NULL,
        product_id      INT             NOT NULL,
        store_id        INT             NOT NULL,
        supplier_id     INT             NOT NULL,
        quantity        INT             NOT NULL,
        unit_price      DECIMAL(10,2)   NOT NULL,
        total_amount    DECIMAL(12,2)   NOT NULL,   -- computed by ETL: qty * unit_price
        loaded_at       DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),

        CONSTRAINT fk_sales_date        FOREIGN KEY (date_id)       REFERENCES dbo.dim_date(date_id),
        CONSTRAINT fk_sales_product     FOREIGN KEY (product_id)    REFERENCES dbo.dim_product(product_id),
        CONSTRAINT fk_sales_store       FOREIGN KEY (store_id)      REFERENCES dbo.dim_store(store_id),
        CONSTRAINT fk_sales_supplier    FOREIGN KEY (supplier_id)   REFERENCES dbo.dim_supplier(supplier_id)
    );
END
GO

-- ============================================================
-- ETL METADATA TABLES
-- (used by the ASP.NET Core dashboard)
-- ============================================================

-- ------------------------------------------------------------
-- etl_pipeline_runs
-- One row per execution of the Python ETL pipeline
-- ------------------------------------------------------------
IF OBJECT_ID('dbo.etl_pipeline_runs', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.etl_pipeline_runs (
        run_id          INT             NOT NULL IDENTITY(1,1) PRIMARY KEY,
        pipeline_name   VARCHAR(100)    NOT NULL,
        source_file     VARCHAR(300)    NULL,           -- CSV path or API endpoint
        start_time      DATETIME2       NOT NULL,
        end_time        DATETIME2       NULL,
        status          VARCHAR(20)     NOT NULL        -- 'running' | 'success' | 'failed'
                        CONSTRAINT chk_run_status CHECK (status IN ('running', 'success', 'failed')),
        rows_ingested   INT             NOT NULL DEFAULT 0,
        rows_failed     INT             NOT NULL DEFAULT 0,
        error_message   NVARCHAR(2000)  NULL
    );
END
GO

-- ------------------------------------------------------------
-- etl_data_quality_log
-- One row per data-quality check per pipeline run
-- ------------------------------------------------------------
IF OBJECT_ID('dbo.etl_data_quality_log', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.etl_data_quality_log (
        log_id          INT             NOT NULL IDENTITY(1,1) PRIMARY KEY,
        run_id          INT             NOT NULL,
        check_name      VARCHAR(100)    NOT NULL,       -- e.g. 'null_check_quantity'
        passed          BIT             NOT NULL,
        failed_count    INT             NOT NULL DEFAULT 0,
        message         NVARCHAR(500)   NULL,

        CONSTRAINT fk_qlog_run FOREIGN KEY (run_id) REFERENCES dbo.etl_pipeline_runs(run_id)
    );
END
GO

-- ------------------------------------------------------------
-- etl_rejected_rows
-- Bad rows the pipeline couldn't load — kept for debugging
-- ------------------------------------------------------------
IF OBJECT_ID('dbo.etl_rejected_rows', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.etl_rejected_rows (
        reject_id       INT             NOT NULL IDENTITY(1,1) PRIMARY KEY,
        run_id          INT             NOT NULL,
        source_row      NVARCHAR(MAX)   NOT NULL,       -- raw JSON of the bad row
        rejection_reason VARCHAR(500)   NOT NULL,
        rejected_at     DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),

        CONSTRAINT fk_reject_run FOREIGN KEY (run_id) REFERENCES dbo.etl_pipeline_runs(run_id)
    );
END
GO

-- ============================================================
-- INDEXES  (query performance for the dashboard)
-- ============================================================

-- fact_sales — most dashboard queries filter by date + store
CREATE NONCLUSTERED INDEX ix_sales_date
    ON dbo.fact_sales (date_id) INCLUDE (total_amount, quantity);
GO

CREATE NONCLUSTERED INDEX ix_sales_store_date
    ON dbo.fact_sales (store_id, date_id) INCLUDE (total_amount);
GO

CREATE NONCLUSTERED INDEX ix_sales_product
    ON dbo.fact_sales (product_id) INCLUDE (total_amount, quantity);
GO

-- etl tables — dashboard lists runs newest-first
CREATE NONCLUSTERED INDEX ix_runs_start
    ON dbo.etl_pipeline_runs (start_time DESC);
GO

CREATE NONCLUSTERED INDEX ix_qlog_run
    ON dbo.etl_data_quality_log (run_id);
GO

-- ============================================================
-- DONE
-- Run this script once in SSMS.
-- Next step: Phase 2 — Python ETL pipeline
-- ============================================================

using Dapper;
using Microsoft.Data.SqlClient;
using DataAisle.Web.Models;

namespace DataAisle.Web.Repositories;

public class DashboardRepository
{
    static DashboardRepository()
    {
        Dapper.DefaultTypeMap.MatchNamesWithUnderscores = true;
    }
    private readonly string _conn;
    public DashboardRepository(string connectionString) => _conn = connectionString;

    public async Task<DashboardViewModel> GetDashboardAsync()
    {
        using var db = new SqlConnection(_conn);

        var runs = (await db.QueryAsync<PipelineRun>(
            "SELECT TOP 5 * FROM dbo.etl_pipeline_runs ORDER BY start_time DESC")).ToList();

        var totals = await db.QueryFirstAsync<dynamic>(@"
            SELECT
                ISNULL(SUM(rows_ingested),0) AS TotalRows,
                COUNT(*) AS TotalRuns,
                SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) AS SuccessRuns,
                ISNULL(SUM(rows_failed),0) AS TotalRejected
            FROM dbo.etl_pipeline_runs");

        var qChecks = await db.QueryFirstAsync<dynamic>(@"
            SELECT
                SUM(CASE WHEN passed=1 THEN 1 ELSE 0 END) AS Passed,
                COUNT(*) AS Total
            FROM dbo.etl_data_quality_log");

        var warehouseStats = (await db.QueryAsync<WarehouseStat>(@"
            SELECT 'fact_sales' AS TableName, COUNT(*) AS [RowCount] FROM dbo.fact_sales
            UNION ALL
            SELECT 'dim_product',        COUNT(*) FROM dbo.dim_product
            UNION ALL
            SELECT 'dim_store',          COUNT(*) FROM dbo.dim_store
            UNION ALL
            SELECT 'dim_supplier',       COUNT(*) FROM dbo.dim_supplier
            UNION ALL
            SELECT 'etl_rejected_rows',  COUNT(*) FROM dbo.etl_rejected_rows")).ToList();

        var dailyLoads = (await db.QueryAsync<DailyLoad>(@"
            SELECT CAST(start_time AS DATE) AS Date,
                   ISNULL(SUM(rows_ingested),0) AS RowsLoaded
            FROM dbo.etl_pipeline_runs
            WHERE status = 'success'
              AND start_time >= DATEADD(day,-30,GETUTCDATE())
            GROUP BY CAST(start_time AS DATE)
            ORDER BY Date")).ToList();

        return new DashboardViewModel
        {
            TotalRowsLoaded    = (int)totals.TotalRows,
            TotalRuns          = (int)totals.TotalRuns,
            SuccessfulRuns     = (int)totals.SuccessRuns,
            TotalRejected      = (int)totals.TotalRejected,
            QualityChecksPassed = (int)qChecks.Passed,
            QualityChecksTotal  = (int)qChecks.Total,
            RecentRuns         = runs,
            WarehouseStats     = warehouseStats,
            DailyLoads         = dailyLoads,
        };
    }

    public async Task<List<PipelineRun>> GetAllRunsAsync()
    {
        using var db = new SqlConnection(_conn);
        return (await db.QueryAsync<PipelineRun>(
            "SELECT * FROM dbo.etl_pipeline_runs ORDER BY start_time DESC")).ToList();
    }

    public async Task<RunDetailViewModel?> GetRunDetailAsync(int runId)
    {
        using var db = new SqlConnection(_conn);

        var run = await db.QueryFirstOrDefaultAsync<PipelineRun>(
            "SELECT * FROM dbo.etl_pipeline_runs WHERE run_id = @runId", new { runId });

        if (run == null) return null;

        var checks = (await db.QueryAsync<QualityCheck>(
            "SELECT * FROM dbo.etl_data_quality_log WHERE run_id = @runId ORDER BY log_id",
            new { runId })).ToList();

        var rejectedCount = await db.QueryFirstAsync<int>(
            "SELECT COUNT(*) FROM dbo.etl_rejected_rows WHERE run_id = @runId", new { runId });

        return new RunDetailViewModel
        {
            Run              = run,
            QualityChecks    = checks,
            RejectedRowCount = rejectedCount,
        };
    }

    public async Task<QualityViewModel> GetQualityAsync()
    {
        using var db = new SqlConnection(_conn);

        var recent = (await db.QueryAsync<QualityCheck>(@"
            SELECT TOP 30 q.*, r.start_time
            FROM dbo.etl_data_quality_log q
            JOIN dbo.etl_pipeline_runs r ON q.run_id = r.run_id
            ORDER BY q.log_id DESC")).ToList();

        var summaries = (await db.QueryAsync<CheckSummary>(@"
            SELECT check_name AS CheckName,
                   SUM(CASE WHEN passed=1 THEN 1 ELSE 0 END) AS PassCount,
                   SUM(CASE WHEN passed=0 THEN 1 ELSE 0 END) AS FailCount
            FROM dbo.etl_data_quality_log
            GROUP BY check_name
            ORDER BY check_name")).ToList();

        return new QualityViewModel
        {
            RecentChecks   = recent,
            CheckSummaries = summaries,
        };
    }

    public async Task<WarehouseViewModel> GetWarehouseAsync()
    {
        using var db = new SqlConnection(_conn);

        var tableStats = (await db.QueryAsync<WarehouseStat>(@"
            SELECT 'fact_sales' AS TableName, COUNT(*) AS [RowCount] FROM dbo.fact_sales
            UNION ALL
            SELECT 'dim_product',        COUNT(*) FROM dbo.dim_product
            UNION ALL
            SELECT 'dim_store',          COUNT(*) FROM dbo.dim_store
            UNION ALL
            SELECT 'dim_supplier',       COUNT(*) FROM dbo.dim_supplier
            UNION ALL
            SELECT 'dim_date',           COUNT(*) FROM dbo.dim_date")).ToList();

        var salesTrend = (await db.QueryAsync<DailySales>(@"
            SELECT
                d.full_date AS Date,
                SUM(f.total_amount) AS Revenue,
                SUM(f.quantity) AS Units
            FROM dbo.fact_sales f
            JOIN dbo.dim_date d ON f.date_id = d.date_id
            GROUP BY d.full_date
            ORDER BY d.full_date")).ToList();

        var totals = await db.QueryFirstAsync<dynamic>(@"
            SELECT
                ISNULL(SUM(total_amount),0) AS TotalRevenue,
                ISNULL(SUM(quantity),0)     AS TotalUnits
            FROM dbo.fact_sales");

        return new WarehouseViewModel
        {
            TableStats    = tableStats,
            SalesTrend    = salesTrend,
            TotalRevenue  = (decimal)totals.TotalRevenue,
            TotalUnitsSold = (int)totals.TotalUnits,
        };
    }
}

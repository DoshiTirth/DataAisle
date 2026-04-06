namespace DataAisle.Web.Models;

public class PipelineRun
{
    public int RunId { get; set; }
    public string PipelineName { get; set; } = "";
    public string? SourceFile { get; set; }
    public DateTime StartTime { get; set; }
    public DateTime? EndTime { get; set; }
    public string Status { get; set; } = "";
    public int RowsIngested { get; set; }
    public int RowsFailed { get; set; }
    public string? ErrorMessage { get; set; }

    public string FileName => SourceFile != null
        ? System.IO.Path.GetFileName(SourceFile)
        : "—";

    public TimeSpan? Duration => EndTime.HasValue
        ? EndTime.Value - StartTime
        : null;

    public string DurationDisplay => Duration.HasValue
        ? Duration.Value.TotalSeconds < 60
            ? $"{Duration.Value.TotalSeconds:F1}s"
            : $"{Duration.Value.TotalMinutes:F1}m"
        : "—";
}

public class QualityCheck
{
    public int LogId { get; set; }
    public int RunId { get; set; }
    public string CheckName { get; set; } = "";
    public bool Passed { get; set; }
    public int FailedCount { get; set; }
    public string? Message { get; set; }
}

public class WarehouseStat
{
    public string TableName { get; set; } = "";
    public int RowCount { get; set; }
}

public class DashboardViewModel
{
    public int TotalRowsLoaded { get; set; }
    public int TotalRuns { get; set; }
    public int SuccessfulRuns { get; set; }
    public int TotalRejected { get; set; }
    public int QualityChecksPassed { get; set; }
    public int QualityChecksTotal { get; set; }
    public List<PipelineRun> RecentRuns { get; set; } = new();
    public List<WarehouseStat> WarehouseStats { get; set; } = new();
    public List<DailyLoad> DailyLoads { get; set; } = new();
}

public class DailyLoad
{
    public DateTime Date { get; set; }
    public int RowsLoaded { get; set; }
}

public class RunDetailViewModel
{
    public PipelineRun Run { get; set; } = new();
    public List<QualityCheck> QualityChecks { get; set; } = new();
    public int RejectedRowCount { get; set; }
}

public class QualityViewModel
{
    public List<QualityCheck> RecentChecks { get; set; } = new();
    public List<CheckSummary> CheckSummaries { get; set; } = new();
}

public class CheckSummary
{
    public string CheckName { get; set; } = "";
    public int PassCount { get; set; }
    public int FailCount { get; set; }
}

public class WarehouseViewModel
{
    public List<WarehouseStat> TableStats { get; set; } = new();
    public List<DailySales> SalesTrend { get; set; } = new();
    public decimal TotalRevenue { get; set; }
    public int TotalUnitsSold { get; set; }
}

public class DailySales
{
    public DateTime Date { get; set; }
    public decimal Revenue { get; set; }
    public int Units { get; set; }
}

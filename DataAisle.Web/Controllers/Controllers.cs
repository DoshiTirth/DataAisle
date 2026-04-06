using Microsoft.AspNetCore.Mvc;
using DataAisle.Web.Repositories;

namespace DataAisle.Web.Controllers;

public class DashboardController : Controller
{
    private readonly DashboardRepository _repo;
    public DashboardController(DashboardRepository repo) => _repo = repo;

    public async Task<IActionResult> Index()
    {
        ViewData["Title"]      = "Dashboard overview";
        ViewData["ActivePage"] = "Dashboard";
        var vm = await _repo.GetDashboardAsync();
        return View(vm);
    }
}

public class RunsController : Controller
{
    private readonly DashboardRepository _repo;
    private readonly IConfiguration _config;

    public RunsController(DashboardRepository repo, IConfiguration config)
    {
        _repo   = repo;
        _config = config;
    }

    public async Task<IActionResult> Index()
    {
        ViewData["Title"]      = "Pipeline runs";
        ViewData["ActivePage"] = "Runs";
        var runs = await _repo.GetAllRunsAsync();
        return View(runs);
    }

    public async Task<IActionResult> Detail(int id)
    {
        ViewData["ActivePage"] = "Runs";
        var vm = await _repo.GetRunDetailAsync(id);
        if (vm == null) return NotFound();
        ViewData["Title"]      = $"Run #{id}";
        ViewData["Breadcrumb"] = "Pipeline runs";
        return View(vm);
    }

    public IActionResult Trigger()
    {
        var pythonPath = _config["Pipeline:PythonPath"] ?? "python";
        var scriptPath = _config["Pipeline:ScriptPath"] ?? "";
    
        if (string.IsNullOrEmpty(scriptPath))
        {
            TempData["Error"] = "Pipeline script path not configured in appsettings.json";
            return RedirectToAction("Index");
        }
    
        try
        {
            var psi = new System.Diagnostics.ProcessStartInfo
            {
                FileName               = pythonPath,
                Arguments              = $"\"{scriptPath}\"",
                UseShellExecute        = false,
                RedirectStandardOutput = false,
                CreateNoWindow         = true,
                WorkingDirectory       = System.IO.Path.GetDirectoryName(scriptPath) ?? ""
            };
            System.Diagnostics.Process.Start(psi);
            TempData["Success"] = "Pipeline triggered successfully — check back in a few seconds.";
        }
        catch (Exception ex)
        {
            TempData["Error"] = $"Failed to trigger pipeline: {ex.Message}";
        }
    
        return RedirectToAction("Index", "Dashboard");
    }
}

public class QualityController : Controller
{
    private readonly DashboardRepository _repo;
    public QualityController(DashboardRepository repo) => _repo = repo;

    public async Task<IActionResult> Index()
    {
        ViewData["Title"]      = "Data quality";
        ViewData["ActivePage"] = "Quality";
        var vm = await _repo.GetQualityAsync();
        return View(vm);
    }
}

public class WarehouseController : Controller
{
    private readonly DashboardRepository _repo;
    public WarehouseController(DashboardRepository repo) => _repo = repo;

    public async Task<IActionResult> Index()
    {
        ViewData["Title"]      = "Warehouse stats";
        ViewData["ActivePage"] = "Warehouse";
        var vm = await _repo.GetWarehouseAsync();
        return View(vm);
    }
}

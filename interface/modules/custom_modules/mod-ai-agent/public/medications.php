<?php
/**
 * CareTopicz - Patient medications endpoint (internal only)
 * Returns medication list from prescriptions table for agent use.
 */
$remoteIp = $_SERVER['REMOTE_ADDR'] ?? '';
$isInternal = in_array($remoteIp, ['127.0.0.1', '::1'])
    || strpos($remoteIp, '172.') === 0
    || strpos($remoteIp, '10.') === 0;
if (!$isInternal) {
    http_response_code(403);
    header('Content-Type: application/json');
    echo json_encode(['error' => 'Forbidden - internal access only']);
    exit;
}
header('Content-Type: application/json');

$siteDir = '/var/www/localhost/htdocs/openemr/sites/default';
if (isset($GLOBALS['OE_SITE_DIR'])) {
    $siteDir = $GLOBALS['OE_SITE_DIR'];
}
$sqlConfFile = $siteDir . '/sqlconf.php';
if (!file_exists($sqlConfFile)) {
    echo json_encode(['success' => false, 'error' => 'Database config not found']);
    exit;
}
include $sqlConfFile;

try {
    $dsn = "mysql:host={$host};dbname={$dbase};charset=utf8mb4";
    $pdo = new PDO($dsn, $login, $pass, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);
} catch (PDOException $e) {
    echo json_encode(['success' => false, 'error' => 'Database connection failed']);
    exit;
}

$pid = (int)($_GET['pid'] ?? $_GET['patient_id'] ?? 0);
if (!$pid) {
    echo json_encode(['success' => false, 'error' => 'pid or patient_id required']);
    exit;
}

$includeDiscontinued = ($_GET['include_discontinued'] ?? '0') === '1';

$sql = "SELECT id, drug, dosage, form, route, size, unit, quantity, refills, active, date_added, date_modified
        FROM prescriptions WHERE patient_id = ?";
if (!$includeDiscontinued) {
    $sql .= " AND active = 1";
}
$sql .= " ORDER BY date_added DESC LIMIT 50";

$stmt = $pdo->prepare($sql);
$stmt->execute([$pid]);
$rows = $stmt->fetchAll();

$medications = [];
foreach ($rows as $row) {
    $dose = trim(($row['dosage'] ?? '') . ' ' . ($row['unit'] ?? ''));
    $medications[] = [
        'name' => $row['drug'] ?? 'Unknown',
        'status' => $row['active'] ? 'active' : 'discontinued',
        'dose' => $dose ?: '—',
        'form' => $row['form'] ?? '',
        'route' => $row['route'] ?? '',
        'refills' => (int)($row['refills'] ?? 0),
        'date_added' => $row['date_added'] ?? null,
    ];
}

echo json_encode([
    'success' => true,
    'patient_id' => $pid,
    'medications' => $medications,
    'count' => count($medications),
    'source' => 'OpenEMR prescriptions',
]);

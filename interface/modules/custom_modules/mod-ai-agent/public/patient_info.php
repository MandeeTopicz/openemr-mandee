<?php
/**
 * CareTopicz - Patient demographics endpoint (internal only)
 * Returns patient name, sex, DOB for agent use.
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

$stmt = $pdo->prepare("SELECT pid, fname, lname, sex, DOB FROM patient_data WHERE pid = ?");
$stmt->execute([$pid]);
$row = $stmt->fetch();

if (!$row) {
    echo json_encode(['success' => false, 'error' => 'Patient not found']);
    exit;
}

echo json_encode([
    'success' => true,
    'patient' => [
        'pid' => (int)$row['pid'],
        'fname' => $row['fname'],
        'lname' => $row['lname'],
        'sex' => $row['sex'] ?? null,
        'DOB' => $row['DOB'] ?? null,
    ],
]);

<?php
/**
 * CareTopicz AI Agent - Internal provider list endpoint
 * Returns active authorized providers from OpenEMR database.
 * This endpoint bypasses session auth for internal Docker network requests only.
 */

// Only allow internal Docker network requests
$remoteIp = $_SERVER['REMOTE_ADDR'] ?? '';
$isInternal = in_array($remoteIp, ['127.0.0.1', '::1']) || strpos($remoteIp, '172.') === 0 || strpos($remoteIp, '10.') === 0;

if (!$isInternal) {
    http_response_code(403);
    header('Content-Type: application/json');
    echo json_encode(['error' => 'Forbidden - internal access only']);
    exit;
}

header('Content-Type: application/json');

// Direct database connection instead of globals.php (avoids session requirement)
$siteDir = '/var/www/localhost/htdocs/openemr/sites/default';
$sqlConfFile = $siteDir . '/sqlconf.php';

if (!file_exists($sqlConfFile)) {
    echo json_encode(['error' => 'Database config not found']);
    exit;
}

// Parse sqlconf.php for DB credentials
include($sqlConfFile);

try {
    $dsn = "mysql:host={$host};dbname={$dbase};charset=utf8mb4";
    $pdo = new PDO($dsn, $login, $pass, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);
} catch (PDOException $e) {
    echo json_encode(['error' => 'Database connection failed']);
    exit;
}

$name = $_GET['name'] ?? '';
$sql = "SELECT id, fname, lname, title, specialty, username, npi, organization, street, city, state, zip, phonew1, email FROM users WHERE active = 1 AND authorized = 1";
$params = [];

if ($name) {
    $sql .= " AND (fname LIKE ? OR lname LIKE ? OR CONCAT(fname, ' ', lname) LIKE ?)";
    $search = "%" . $name . "%";
    $params = [$search, $search, $search];
}

$sql .= " ORDER BY lname, fname";

$stmt = $pdo->prepare($sql);
$stmt->execute($params);
$rows = $stmt->fetchAll();

$providers = [];
foreach ($rows as $row) {
    // Derive credential from title or username role
    $credential = $row['title'] ?: '';
    if (!$credential) {
        $uname = strtolower($row['username'] ?? '');
        if ($uname === 'physician' || strpos($uname, 'doc') !== false) {
            $credential = 'MD';
        } elseif ($uname === 'clinician') {
            $credential = 'NP';
        } elseif ($uname === 'admin') {
            $credential = 'MD';
        }
    }
    $displayName = trim($row['fname'] . ' ' . $row['lname']);
    if ($credential) {
        $displayName .= ', ' . $credential;
    }
    $providers[] = [
        'id' => $row['id'],
        'name' => $displayName,
        'first_name' => $row['fname'],
        'last_name' => $row['lname'],
        'credential' => $credential,
        'specialty' => $row['specialty'] ?: 'General',
        'username' => $row['username'],
        'npi' => $row['npi'] ?: null,
        'organization' => $row['organization'] ?: null,
        'city' => $row['city'] ?: null,
        'state' => $row['state'] ?: null,
        'phone' => $row['phonew1'] ?: null,
        'email' => $row['email'] ?: null,
        'source' => 'OpenEMR',
    ];
}

echo json_encode([
    'success' => true,
    'providers' => $providers,
    'total' => count($providers),
]);

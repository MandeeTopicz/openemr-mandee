<?php
/**
 * CareTopicz - Appointment scheduling endpoint (internal only)
 * List providers, check available slots, book appointments.
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

$action = $_GET['action'] ?? $_POST['action'] ?? '';
if (!$action) {
    echo json_encode(['success' => false, 'error' => 'action required']);
    exit;
}

if ($action === 'list_providers') {
    $stmt = $pdo->query(
        "SELECT id, fname, lname, specialty FROM users WHERE active = 1 AND authorized = 1 ORDER BY lname, fname"
    );
    $rows = $stmt->fetchAll();
    $providers = [];
    foreach ($rows as $row) {
        $providers[] = [
            'id' => (int)$row['id'],
            'fname' => $row['fname'],
            'lname' => $row['lname'],
            'specialty' => $row['specialty'] ?? 'General',
        ];
    }
    echo json_encode(['success' => true, 'providers' => $providers]);
    exit;
}

if ($action === 'available_slots') {
    $providerId = (string)($_GET['provider_id'] ?? $_POST['provider_id'] ?? '');
    $startDate = $_GET['start_date'] ?? $_POST['start_date'] ?? '';
    $endDate = $_GET['end_date'] ?? $_POST['end_date'] ?? '';
    $timePreference = $_GET['time_preference'] ?? $_POST['time_preference'] ?? null;

    if (!$providerId || !$startDate || !$endDate) {
        echo json_encode(['success' => false, 'error' => 'provider_id, start_date, end_date required']);
        exit;
    }

    $startTs = strtotime($startDate);
    $endTs = strtotime($endDate);
    if ($startTs === false || $endTs === false || $startTs > $endTs) {
        echo json_encode(['success' => false, 'error' => 'Invalid start_date or end_date']);
        exit;
    }

    $stmt = $pdo->prepare(
        "SELECT pc_eventDate, pc_startTime, pc_endTime FROM openemr_postcalendar_events
         WHERE pc_aid = ? AND pc_eventDate >= ? AND pc_eventDate <= ?
         AND pc_eventstatus = 1 ORDER BY pc_eventDate, pc_startTime"
    );
    $stmt->execute([$providerId, $startDate, $endDate]);
    $booked = $stmt->fetchAll();

    $bookedSlots = [];
    foreach ($booked as $b) {
        $d = $b['pc_eventDate'];
        $st = $b['pc_startTime'];
        $et = $b['pc_endTime'];
        for ($t = strtotime($d . ' ' . $st); $t < strtotime($d . ' ' . $et); $t += 1800) {
            $bookedSlots[] = date('Y-m-d', $t) . ' ' . date('H:i:s', $t);
        }
    }
    $bookedSet = array_flip($bookedSlots);

    $minStart = 9 * 3600;
    $maxEnd = 17 * 3600;
    if ($timePreference === 'morning') {
        $minStart = 9 * 3600;
        $maxEnd = 11 * 3600 + 1800;
    } elseif ($timePreference === 'late_morning') {
        $minStart = 11 * 3600;
        $maxEnd = 13 * 3600;
    } elseif ($timePreference === 'afternoon') {
        $minStart = 13 * 3600;
        $maxEnd = 17 * 3600;
    }

    $slots = [];
    for ($d = $startTs; $d <= $endTs; $d += 86400) {
        $dateStr = date('Y-m-d', $d);
        for ($t = $minStart; $t < $maxEnd; $t += 1800) {
            $slotTime = $dateStr . ' ' . sprintf('%02d:%02d:00', floor($t / 3600), ($t % 3600) / 60);
            $key = $slotTime;
            if (!isset($bookedSet[$key])) {
                $slots[] = [
                    'date' => $dateStr,
                    'start_time' => sprintf('%02d:%02d:00', floor($t / 3600), ($t % 3600) / 60),
                ];
                if (count($slots) >= 10) {
                    break 2;
                }
            }
        }
    }
    echo json_encode(['success' => true, 'slots' => $slots]);
    exit;
}

if ($action === 'book_appointment') {
    $providerId = (string)($_GET['provider_id'] ?? $_POST['provider_id'] ?? '');
    $patientId = (string)($_GET['patient_id'] ?? $_POST['patient_id'] ?? '');
    $date = $_GET['date'] ?? $_POST['date'] ?? '';
    $startTime = $_GET['start_time'] ?? $_POST['start_time'] ?? '';
    $duration = (int)($_GET['duration'] ?? $_POST['duration'] ?? 900);
    $title = $_GET['title'] ?? $_POST['title'] ?? 'Office Visit';

    if (!$providerId || !$patientId || !$date || !$startTime) {
        echo json_encode(['success' => false, 'error' => 'provider_id, patient_id, date, start_time required']);
        exit;
    }

    $startTs = strtotime($date . ' ' . $startTime);
    if ($startTs === false) {
        echo json_encode(['success' => false, 'error' => 'Invalid date or start_time']);
        exit;
    }
    $endTs = $startTs + $duration;
    $endTime = date('H:i:s', $endTs);

    $stmt = $pdo->prepare(
        "INSERT INTO openemr_postcalendar_events
         (pc_aid, pc_pid, pc_eventDate, pc_endDate, pc_startTime, pc_endTime, pc_duration, pc_title,
          pc_catid, pc_apptstatus, pc_eventstatus, pc_multiple)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, 5, '-', 1, 0)"
    );
    $stmt->execute([
        $providerId,
        $patientId,
        $date,
        $date,
        $startTime,
        $endTime,
        $duration,
        $title,
    ]);
    $eid = (int)$pdo->lastInsertId();
    echo json_encode(['success' => true, 'pc_eid' => $eid]);
    exit;
}

echo json_encode(['success' => false, 'error' => 'Unknown action']);

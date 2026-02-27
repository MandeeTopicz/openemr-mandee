<?php
/**
 * CareTopicz Bounty - Regulated Medication Schedule CRUD
 * Internal-only endpoint for agent and clinic staff.
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

// Parse JSON body for POST
$body = [];
if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($raw = file_get_contents('php://input'))) {
    $body = json_decode($raw, true) ?: [];
}

function jsonResp($data) {
    echo json_encode($data);
}

function getProtocol($pdo, $medication, $patientCategory) {
    $cat = $patientCategory;
    if ($patientCategory === 'all') {
        $cat = 'all';
    }
    $stmt = $pdo->prepare("
        SELECT * FROM medication_protocols
        WHERE medication_name = ? AND patient_category = ?
    ");
    $stmt->execute([$medication, $cat]);
    $row = $stmt->fetch();
    if (!$row) {
        $stmt = $pdo->prepare("
            SELECT * FROM medication_protocols
            WHERE medication_name = ? AND (patient_category = ? OR patient_category = 'all')
            ORDER BY patient_category = 'all' ASC
            LIMIT 1
        ");
        $stmt->execute([$medication, $cat]);
        $row = $stmt->fetch();
    }
    return $row;
}

function calcDueDates($steps, $startDate, $prevCompletedDate = null) {
    $dueDates = [];
    $prev = $prevCompletedDate ? strtotime($prevCompletedDate) : strtotime($startDate);
    foreach ($steps as $i => $step) {
        $step = is_string($step) ? json_decode($step, true) : $step;
        if (!$step) continue;
        $daysFromPrev = $step['days_from_prev'] ?? $step['days_from_start'] ?? 0;
        $windowDays = $step['window_days'] ?? 7;
        $due = strtotime("+{$daysFromPrev} days", $prev);
        $dueDate = date('Y-m-d', $due);
        $windowEnd = date('Y-m-d', strtotime("+{$windowDays} days", $due));
        $dueDates[] = [
            'step_number' => $i + 1,
            'step_name' => $step['name'],
            'step_type' => $step['type'],
            'description' => $step['description'] ?? null,
            'due_date' => $dueDate,
            'window_start' => $dueDate,
            'window_end' => $windowEnd,
        ];
        $prev = $due;
    }
    return $dueDates;
}

switch ($action) {
    case 'get_protocols':
        $medication = $_GET['medication'] ?? '';
        $sql = "SELECT id, medication_name, protocol_type, patient_category, source FROM medication_protocols";
        $params = [];
        if ($medication) {
            $sql .= " WHERE medication_name = ?";
            $params[] = $medication;
        }
        $sql .= " ORDER BY medication_name, patient_category";
        $stmt = $pdo->prepare($sql);
        $stmt->execute($params);
        $rows = $stmt->fetchAll();
        jsonResp(['success' => true, 'protocols' => $rows]);
        break;

    case 'get_schedule':
        $patientId = (int)($_GET['patient_id'] ?? 0);
        if (!$patientId) {
            jsonResp(['success' => false, 'error' => 'patient_id required']);
            break;
        }
        $stmt = $pdo->prepare("
            SELECT s.*, p.medication_name, p.protocol_type, p.patient_category
            FROM patient_med_schedules s
            JOIN medication_protocols p ON p.id = s.protocol_id
            WHERE s.patient_id = ? AND s.status NOT IN ('completed', 'cancelled')
        ");
        $stmt->execute([$patientId]);
        $schedules = $stmt->fetchAll();
        $milestones = [];
        foreach ($schedules as &$sch) {
            $mStmt = $pdo->prepare("SELECT * FROM schedule_milestones WHERE schedule_id = ? ORDER BY step_number");
            $mStmt->execute([$sch['id']]);
            $sch['milestones'] = $mStmt->fetchAll();
            $milestones = array_merge($milestones, $sch['milestones']);
        }
        jsonResp(['success' => true, 'schedules' => $schedules]);
        break;

    case 'get_dashboard_alerts':
        $stmt = $pdo->prepare("
            SELECT m.*, s.patient_id, s.status as schedule_status, p.medication_name, p.protocol_type
            FROM schedule_milestones m
            JOIN patient_med_schedules s ON s.id = m.schedule_id
            JOIN medication_protocols p ON p.id = s.protocol_id
            WHERE m.status IN ('pending', 'scheduled', 'overdue')
            AND s.status IN ('initiating', 'active', 'completing')
            AND (m.due_date <= DATE_ADD(CURDATE(), INTERVAL 7 DAY) OR m.window_end <= DATE_ADD(CURDATE(), INTERVAL 3 DAY))
            ORDER BY m.due_date
        ");
        $stmt->execute();
        jsonResp(['success' => true, 'alerts' => $stmt->fetchAll()]);
        break;

    case 'get_all_active':
        $stmt = $pdo->prepare("
            SELECT s.*, p.medication_name, p.protocol_type,
                   (SELECT COUNT(*) FROM schedule_milestones WHERE schedule_id = s.id AND status IN ('pending','overdue')) as pending_count
            FROM patient_med_schedules s
            JOIN medication_protocols p ON p.id = s.protocol_id
            WHERE s.status IN ('initiating', 'active', 'completing')
        ");
        $stmt->execute();
        jsonResp(['success' => true, 'schedules' => $stmt->fetchAll()]);
        break;

    case 'create_schedule':
        $patientId = (int)($body['patient_id'] ?? 0);
        $medication = trim($body['medication'] ?? '');
        $patientCategory = $body['patient_category'] ?? 'male';
        $createdBy = $body['created_by'] ?? 'agent';
        $startDate = $body['start_date'] ?? date('Y-m-d');

        if (!$patientId || !$medication) {
            jsonResp(['success' => false, 'error' => 'patient_id and medication required']);
            break;
        }

        $protocol = getProtocol($pdo, $medication, $patientCategory);
        if (!$protocol) {
            jsonResp(['success' => false, 'error' => "No protocol found for {$medication} / {$patientCategory}"]);
            break;
        }

        $existStmt = $pdo->prepare("
            SELECT id FROM patient_med_schedules
            WHERE patient_id = ? AND protocol_id = ? AND status IN ('initiating','active','completing')
        ");
        $existStmt->execute([$patientId, $protocol['id']]);
        if ($existStmt->fetch()) {
            jsonResp(['success' => false, 'error' => 'Active schedule already exists for this patient and medication']);
            break;
        }

        $pdo->beginTransaction();
        try {
            $ins = $pdo->prepare("
                INSERT INTO patient_med_schedules (patient_id, protocol_id, patient_category, status, created_by, start_date)
                VALUES (?, ?, ?, 'initiating', ?, ?)
            ");
            $ins->execute([$patientId, $protocol['id'], $patientCategory, $createdBy, $startDate]);
            $scheduleId = $pdo->lastInsertId();

            $steps = json_decode($protocol['steps'], true);
            if ($steps) {
                $milestoneIns = $pdo->prepare("
                    INSERT INTO schedule_milestones (schedule_id, step_number, step_name, step_type, description, due_date, window_start, window_end)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ");
                $prevDate = $startDate;
                foreach ($steps as $i => $step) {
                    $daysFromPrev = $step['days_from_prev'] ?? $step['days_from_start'] ?? 0;
                    $windowDays = $step['window_days'] ?? 7;
                    $due = date('Y-m-d', strtotime("+{$daysFromPrev} days", strtotime($prevDate)));
                    $windowEnd = date('Y-m-d', strtotime("+{$windowDays} days", strtotime($due)));
                    $milestoneIns->execute([
                        $scheduleId,
                        $i + 1,
                        $step['name'],
                        $step['type'],
                        $step['description'] ?? null,
                        $due,
                        $due,
                        $windowEnd,
                    ]);
                }
            }

            $monthlyCycle = json_decode($protocol['monthly_cycle'] ?? '{}', true);
            $durationMonths = $monthlyCycle['typical_duration_months'] ?? 6;
            if ($durationMonths && !empty($monthlyCycle['steps'])) {
                $cycleSteps = $monthlyCycle['steps'];
                $stepNum = count($steps) + 1;
                $firstPrescDate = $startDate;
                foreach ($steps as $st) {
                    if (($st['name'] ?? '') === 'first_prescription') {
                        $firstPrescDate = date('Y-m-d', strtotime($st['window_end'] ?? $startDate));
                        break;
                    }
                }
                for ($m = 1; $m <= $durationMonths; $m++) {
                    $monthStart = date('Y-m-d', strtotime("+{$m} months", strtotime($firstPrescDate)));
                    foreach ($cycleSteps as $cs) {
                        $due = $monthStart;
                        $windowEnd = date('Y-m-d', strtotime('+7 days', strtotime($due)));
                        $mIns = $pdo->prepare("
                            INSERT INTO schedule_milestones (schedule_id, step_number, step_name, step_type, description, due_date, window_start, window_end)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ");
                        $mIns->execute([
                            $scheduleId,
                            $stepNum++,
                            $cs['name'] . '_m' . $m,
                            $cs['type'],
                            $cs['description'] ?? null,
                            $due,
                            $due,
                            $windowEnd,
                        ]);
                    }
                }
            }

            $pdo->commit();

            $schedStmt = $pdo->prepare("SELECT * FROM patient_med_schedules WHERE id = ?");
            $schedStmt->execute([$scheduleId]);
            $schedule = $schedStmt->fetch();
            $mStmt = $pdo->prepare("SELECT * FROM schedule_milestones WHERE schedule_id = ? ORDER BY step_number");
            $mStmt->execute([$scheduleId]);
            $schedule['milestones'] = $mStmt->fetchAll();

            jsonResp(['success' => true, 'schedule' => $schedule]);
        } catch (Exception $e) {
            $pdo->rollBack();
            jsonResp(['success' => false, 'error' => $e->getMessage()]);
        }
        break;

    case 'complete_milestone':
        $milestoneId = (int)($body['milestone_id'] ?? 0);
        $completedBy = $body['completed_by'] ?? 'agent';
        $completedDate = $body['completed_date'] ?? date('Y-m-d');
        $notes = $body['notes'] ?? '';

        if (!$milestoneId) {
            jsonResp(['success' => false, 'error' => 'milestone_id required']);
            break;
        }

        $mStmt = $pdo->prepare("SELECT * FROM schedule_milestones WHERE id = ?");
        $mStmt->execute([$milestoneId]);
        $milestone = $mStmt->fetch();
        if (!$milestone) {
            jsonResp(['success' => false, 'error' => 'Milestone not found']);
            break;
        }

        $upd = $pdo->prepare("
            UPDATE schedule_milestones SET status = 'completed', completed_date = ?, completed_by = ?, notes = ?
            WHERE id = ?
        ");
        $upd->execute([$completedDate, $completedBy, $notes, $milestoneId]);

        $schedStmt = $pdo->prepare("SELECT * FROM patient_med_schedules WHERE id = ?");
        $schedStmt->execute([$milestone['schedule_id']]);
        $schedule = $schedStmt->fetch();
        $mStmt = $pdo->prepare("SELECT * FROM schedule_milestones WHERE schedule_id = ? ORDER BY step_number");
        $mStmt->execute([$milestone['schedule_id']]);
        $schedule['milestones'] = $mStmt->fetchAll();

        jsonResp(['success' => true, 'schedule' => $schedule]);
        break;

    case 'cancel_schedule':
        $scheduleId = (int)($body['schedule_id'] ?? 0);
        $reason = $body['cancelled_reason'] ?? $body['reason'] ?? 'Cancelled';
        $cancelledBy = $body['cancelled_by'] ?? $body['completed_by'] ?? 'agent';

        if (!$scheduleId) {
            jsonResp(['success' => false, 'error' => 'schedule_id required']);
            break;
        }

        $pdo->prepare("UPDATE patient_med_schedules SET status = 'cancelled', cancelled_reason = ? WHERE id = ?")
            ->execute([$reason, $scheduleId]);
        $pdo->prepare("UPDATE schedule_milestones SET status = 'cancelled' WHERE schedule_id = ? AND status IN ('pending','scheduled','overdue')")
            ->execute([$scheduleId]);

        jsonResp(['success' => true, 'message' => 'Schedule cancelled']);
        break;

    case 'reschedule_milestone':
        $milestoneId = (int)($body['milestone_id'] ?? 0);
        $newDueDate = $body['new_due_date'] ?? '';
        $rescheduledBy = $body['rescheduled_by'] ?? 'agent';

        if (!$milestoneId || !$newDueDate) {
            jsonResp(['success' => false, 'error' => 'milestone_id and new_due_date required']);
            break;
        }

        $mStmt = $pdo->prepare("SELECT * FROM schedule_milestones WHERE id = ?");
        $mStmt->execute([$milestoneId]);
        $milestone = $mStmt->fetch();
        if (!$milestone) {
            jsonResp(['success' => false, 'error' => 'Milestone not found']);
            break;
        }

        $windowEnd = $milestone['window_end'];
        $warnings = [];
        if ($windowEnd && $newDueDate > $windowEnd) {
            $warnings[] = 'New date is outside the compliance window';
        }

        $upd = $pdo->prepare("UPDATE schedule_milestones SET due_date = ?, window_start = ? WHERE id = ?");
        $upd->execute([$newDueDate, $newDueDate, $milestoneId]);

        $schedStmt = $pdo->prepare("SELECT * FROM patient_med_schedules WHERE id = ?");
        $schedStmt->execute([$milestone['schedule_id']]);
        $schedule = $schedStmt->fetch();
        $mStmt = $pdo->prepare("SELECT * FROM schedule_milestones WHERE schedule_id = ? ORDER BY step_number");
        $mStmt->execute([$milestone['schedule_id']]);
        $schedule['milestones'] = $mStmt->fetchAll();

        jsonResp(['success' => true, 'schedule' => $schedule, 'warnings' => $warnings]);
        break;

    case 'check_conflicts':
        $scheduleId = (int)($_GET['schedule_id'] ?? 0);
        if (!$scheduleId) {
            jsonResp(['success' => false, 'error' => 'schedule_id required']);
            break;
        }

        $today = date('Y-m-d');
        $stmt = $pdo->prepare("
            SELECT * FROM schedule_milestones
            WHERE schedule_id = ? AND status IN ('pending', 'scheduled')
        ");
        $stmt->execute([$scheduleId]);
        $milestones = $stmt->fetchAll();
        $conflicts = [];

        foreach ($milestones as $m) {
            if ($m['due_date'] < $today) {
                $conflicts[] = ['milestone_id' => $m['id'], 'severity' => 'critical', 'message' => 'Overdue: ' . $m['step_name']];
            } elseif ($m['window_end'] && $m['window_end'] <= date('Y-m-d', strtotime('+3 days'))) {
                $conflicts[] = ['milestone_id' => $m['id'], 'severity' => 'warning', 'message' => 'Compliance window expiring: ' . $m['step_name']];
            }
        }

        jsonResp(['success' => true, 'conflicts' => $conflicts]);
        break;

    default:
        jsonResp(['success' => false, 'error' => 'Unknown action']);
}

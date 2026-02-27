<?php
/**
 * CareTopicz Bounty - Regulated Medication Coordination Engine
 * Database migration: creates medication_protocols, patient_med_schedules, schedule_milestones
 * Run once from internal Docker network.
 */

// Only allow internal Docker network requests
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
    echo json_encode(['error' => 'Database config not found', 'path' => $sqlConfFile]);
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
    echo json_encode(['error' => 'Database connection failed']);
    exit;
}

$pdo->exec("
CREATE TABLE IF NOT EXISTS medication_protocols (
    id INT AUTO_INCREMENT PRIMARY KEY,
    medication_name VARCHAR(100) NOT NULL,
    protocol_type VARCHAR(50) NOT NULL,
    patient_category VARCHAR(50) NOT NULL,
    steps JSON NOT NULL,
    monthly_cycle JSON DEFAULT NULL,
    completion_steps JSON DEFAULT NULL,
    source VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_protocol (medication_name, protocol_type, patient_category)
);
");

$pdo->exec("
CREATE TABLE IF NOT EXISTS patient_med_schedules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id BIGINT NOT NULL,
    protocol_id INT NOT NULL,
    patient_category VARCHAR(50) NOT NULL,
    status ENUM('initiating', 'active', 'completing', 'completed', 'cancelled', 'paused') DEFAULT 'initiating',
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    cancelled_reason TEXT DEFAULT NULL,
    current_step INT DEFAULT 1,
    start_date DATE DEFAULT NULL,
    expected_end_date DATE DEFAULT NULL,
    notes TEXT DEFAULT NULL,
    FOREIGN KEY (protocol_id) REFERENCES medication_protocols(id),
    KEY idx_patient (patient_id),
    KEY idx_status (status)
);
");

$pdo->exec("
CREATE TABLE IF NOT EXISTS schedule_milestones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    schedule_id INT NOT NULL,
    step_number INT NOT NULL,
    step_name VARCHAR(100) NOT NULL,
    step_type VARCHAR(50) NOT NULL,
    description TEXT DEFAULT NULL,
    status ENUM('pending', 'scheduled', 'completed', 'overdue', 'skipped', 'cancelled') DEFAULT 'pending',
    due_date DATE NOT NULL,
    window_start DATE DEFAULT NULL,
    window_end DATE DEFAULT NULL,
    completed_date DATE DEFAULT NULL,
    completed_by VARCHAR(100) DEFAULT NULL,
    appointment_id INT DEFAULT NULL,
    notes TEXT DEFAULT NULL,
    FOREIGN KEY (schedule_id) REFERENCES patient_med_schedules(id) ON DELETE CASCADE,
    KEY idx_schedule_status (schedule_id, status),
    KEY idx_due_date (due_date)
);
");

// Seed medication_protocols
$protocols = [
    [
        'medication_name' => 'isotretinoin',
        'protocol_type' => 'ipledge',
        'patient_category' => 'fcbp',
        'source' => 'FDA iPLEDGE REMS Program',
        'steps' => json_encode([
            ['step' => 1, 'name' => 'ipledge_registration', 'type' => 'confirmation', 'description' => 'Register patient in iPLEDGE system', 'days_from_start' => 0, 'window_days' => 7],
            ['step' => 2, 'name' => 'contraception_counseling', 'type' => 'office_visit', 'description' => 'Document two forms of contraception or abstinence commitment', 'days_from_start' => 0, 'window_days' => 7],
            ['step' => 3, 'name' => 'pregnancy_test_1', 'type' => 'lab', 'description' => 'First negative pregnancy test', 'days_from_start' => 0, 'window_days' => 7],
            ['step' => 4, 'name' => 'pregnancy_test_2', 'type' => 'lab', 'description' => 'Second negative pregnancy test, at least 30 days after first', 'days_from_prev' => 30, 'window_days' => 7],
            ['step' => 5, 'name' => 'first_prescription', 'type' => 'prescription', 'description' => 'First isotretinoin prescription — within 7 days of second pregnancy test', 'days_from_prev' => 0, 'window_days' => 7],
        ]),
        'monthly_cycle' => json_encode([
            'description' => 'Repeats each month while on treatment',
            'typical_duration_months' => 6,
            'steps' => [
                ['name' => 'monthly_pregnancy_test', 'type' => 'lab', 'description' => 'Negative pregnancy test within 7 days before prescription', 'window_days_before_prescription' => 7],
                ['name' => 'monthly_office_visit', 'type' => 'office_visit', 'description' => 'Monthly provider visit'],
                ['name' => 'ipledge_monthly_confirmation', 'type' => 'confirmation', 'description' => 'iPLEDGE system confirmation — days 19-23 of each 30-day cycle'],
                ['name' => 'monthly_prescription', 'type' => 'prescription', 'description' => 'Monthly isotretinoin prescription — 7-day pickup window', 'window_days' => 7],
            ],
        ]),
        'completion_steps' => json_encode([['name' => 'final_pregnancy_test', 'type' => 'lab', 'description' => 'Pregnancy test 30 days after last dose', 'days_after_last_dose' => 30]]),
    ],
    [
        'medication_name' => 'isotretinoin',
        'protocol_type' => 'ipledge',
        'patient_category' => 'male',
        'source' => 'FDA iPLEDGE REMS Program',
        'steps' => json_encode([
            ['step' => 1, 'name' => 'ipledge_registration', 'type' => 'confirmation', 'description' => 'Register patient in iPLEDGE system', 'days_from_start' => 0, 'window_days' => 7],
            ['step' => 2, 'name' => 'baseline_labs', 'type' => 'lab', 'description' => 'Baseline labs: CBC, lipid panel, liver function, fasting glucose', 'days_from_start' => 0, 'window_days' => 14],
            ['step' => 3, 'name' => 'first_prescription', 'type' => 'prescription', 'description' => 'First isotretinoin prescription', 'days_from_prev' => 0, 'window_days' => 7],
        ]),
        'monthly_cycle' => json_encode([
            'description' => 'Repeats each month while on treatment',
            'typical_duration_months' => 6,
            'steps' => [
                ['name' => 'monthly_labs', 'type' => 'lab', 'description' => 'Monthly labs: lipid panel, liver function'],
                ['name' => 'monthly_office_visit', 'type' => 'office_visit', 'description' => 'Monthly provider visit'],
                ['name' => 'ipledge_monthly_confirmation', 'type' => 'confirmation', 'description' => 'iPLEDGE system confirmation'],
                ['name' => 'monthly_prescription', 'type' => 'prescription', 'description' => 'Monthly isotretinoin prescription — 7-day pickup window', 'window_days' => 7],
            ],
        ]),
        'completion_steps' => json_encode([]),
    ],
    [
        'medication_name' => 'isotretinoin',
        'protocol_type' => 'ipledge',
        'patient_category' => 'non_fcbp_female',
        'source' => 'FDA iPLEDGE REMS Program',
        'steps' => json_encode([
            ['step' => 1, 'name' => 'ipledge_registration', 'type' => 'confirmation', 'description' => 'Register patient in iPLEDGE system', 'days_from_start' => 0, 'window_days' => 7],
            ['step' => 2, 'name' => 'baseline_labs', 'type' => 'lab', 'description' => 'Baseline labs: CBC, lipid panel, liver function', 'days_from_start' => 0, 'window_days' => 14],
            ['step' => 3, 'name' => 'first_prescription', 'type' => 'prescription', 'description' => 'First isotretinoin prescription', 'days_from_prev' => 0, 'window_days' => 7],
        ]),
        'monthly_cycle' => json_encode([
            'description' => 'Repeats each month while on treatment',
            'typical_duration_months' => 6,
            'steps' => [
                ['name' => 'monthly_labs', 'type' => 'lab', 'description' => 'Monthly labs: lipid panel, liver function'],
                ['name' => 'monthly_office_visit', 'type' => 'office_visit', 'description' => 'Monthly provider visit'],
                ['name' => 'ipledge_monthly_confirmation', 'type' => 'confirmation', 'description' => 'iPLEDGE system confirmation'],
                ['name' => 'monthly_prescription', 'type' => 'prescription', 'description' => 'Monthly isotretinoin prescription', 'window_days' => 7],
            ],
        ]),
        'completion_steps' => json_encode([]),
    ],
    [
        'medication_name' => 'adalimumab',
        'protocol_type' => 'biologic',
        'patient_category' => 'all',
        'source' => 'FDA Prescribing Information / AbbVie',
        'steps' => json_encode([
            ['step' => 1, 'name' => 'tb_screening', 'type' => 'lab', 'description' => 'TB test before starting', 'days_from_start' => 0, 'window_days' => 30],
            ['step' => 2, 'name' => 'hepatitis_screening', 'type' => 'lab', 'description' => 'Hepatitis B and C screening', 'days_from_start' => 0, 'window_days' => 30],
            ['step' => 3, 'name' => 'baseline_labs', 'type' => 'lab', 'description' => 'CBC, CMP, liver function tests', 'days_from_start' => 0, 'window_days' => 14],
            ['step' => 4, 'name' => 'prior_authorization', 'type' => 'confirmation', 'description' => 'Insurance prior authorization approval', 'days_from_start' => 0, 'window_days' => 30],
            ['step' => 5, 'name' => 'first_injection', 'type' => 'injection', 'description' => 'First injection — loading dose may apply', 'days_from_prev' => 0, 'window_days' => 7],
        ]),
        'monthly_cycle' => json_encode([
            'description' => 'Every 14 days (biweekly injection)',
            'interval_days' => 14,
            'typical_duration_months' => null,
            'steps' => [
                ['name' => 'biweekly_injection', 'type' => 'injection', 'description' => 'Adalimumab injection every 14 days'],
            ],
            'labs_every_n_months' => 3,
            'lab_steps' => [
                ['name' => 'quarterly_labs', 'type' => 'lab', 'description' => 'CBC, CMP every 3 months'],
            ],
        ]),
        'completion_steps' => json_encode([]),
    ],
];

$stmt = $pdo->prepare("
    INSERT IGNORE INTO medication_protocols (medication_name, protocol_type, patient_category, steps, monthly_cycle, completion_steps, source)
    VALUES (?, ?, ?, ?, ?, ?, ?)
");
foreach ($protocols as $p) {
    $stmt->execute([
        $p['medication_name'],
        $p['protocol_type'],
        $p['patient_category'],
        $p['steps'],
        $p['monthly_cycle'],
        $p['completion_steps'],
        $p['source'],
    ]);
}

$inserted = $stmt->rowCount();
echo json_encode([
    'success' => true,
    'message' => 'Migration complete',
    'tables' => ['medication_protocols', 'patient_med_schedules', 'schedule_milestones'],
    'protocols_seeded' => $inserted,
]);

(function () {
    "use strict";

    const VERSION = "1.1.0";

    const CONFIG = {
        logoPath: "assets/pratirup-logo.png",
        reportTitle: "PRATIRUP",
        reportSubtitle: "DIGITAL TWIN MISSION REPORT SYSTEM",
        classification: "POST-FLIGHT ENGINE HEALTH & MISSION INTELLIGENCE REPORT",
        footerLeft: "Created by PRATIRUP",
        footerRight: "Designed by QubitX"
    };

    let latestReport = null;

    function number(
        value,
        fallback = null
    ) {
        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {
            return fallback;
        }

        const n = Number(value);

        return Number.isFinite(n)
            ? n
            : fallback;
    }

    function text(
        value,
        fallback = "--"
    ) {
        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {
            return fallback;
        }

        return String(value);
    }

    function round(
        value,
        digits = 1
    ) {
        const n =
            number(value);

        if (
            n === null
        ) {
            return "--";
        }

        return n.toFixed(digits);
    }

    function clone(
        value
    ) {
        if (
            value === null ||
            value === undefined
        ) {
            return value;
        }

        if (
            typeof structuredClone ===
            "function"
        ) {
            try {
                return structuredClone(
                    value
                );
            }
            catch (_) {}
        }

        try {
            return JSON.parse(
                JSON.stringify(
                    value
                )
            );
        }
        catch (_) {
            return value;
        }
    }

    function escapeHTML(
        value
    ) {
        return text(
            value,
            ""
        )
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function formatDateTime(
        timestamp
    ) {
        if (!timestamp) {
            return "--";
        }

        try {
            return new Date(
                timestamp
            ).toLocaleString();
        }
        catch (_) {
            return "--";
        }
    }

    function formatDuration(
        milliseconds
    ) {
        const ms =
            number(
                milliseconds,
                0
            );

        const totalSeconds =
            Math.floor(
                ms / 1000
            );

        const hours =
            Math.floor(
                totalSeconds / 3600
            );

        const minutes =
            Math.floor(
                (
                    totalSeconds %
                    3600
                ) /
                60
            );

        const seconds =
            totalSeconds %
            60;

        return [
            hours,
            minutes,
            seconds
        ]
            .map(
                item =>
                    String(item)
                        .padStart(
                            2,
                            "0"
                        )
            )
            .join(":");
    }

    function getModuleLatest(
        objectName
    ) {
        const module =
            window[
                objectName
            ];

        if (
            !module ||
            typeof module.getLatest !==
            "function"
        ) {
            return null;
        }

        try {
            return clone(
                module.getLatest()
            );
        }
        catch (error) {
            console.warn(
                `[PRATIRUP Report] Unable to read ${objectName}`,
                error
            );

            return null;
        }
    }

    function getMissionReplay() {
        const replay =
            window
                .PratirupMissionReplay;

        if (!replay) {
            return null;
        }

        let mission =
            null;

        let controllerState =
            null;

        try {
            mission =
                typeof replay.getMission ===
                "function"
                    ? replay.getMission()
                    : null;
        }
        catch (_) {}

        try {
            controllerState =
                typeof replay.getState ===
                "function"
                    ? replay.getState()
                    : null;
        }
        catch (_) {}

        const status =
            mission?.status ||
            controllerState?.status ||
            null;

        const id =
            mission?.id ??
            controllerState
                ?.loadedMissionId ??
            status
                ?.mission_id ??
            status
                ?.missionId ??
            null;

        if (
            !id &&
            !mission &&
            !controllerState
        ) {
            return null;
        }

        const elapsedSeconds =
            number(
                status
                    ?.elapsed_seconds,
                null
            );

        return {
            ...(
                mission ||
                {}
            ),

            id,

            status,

            controllerState,

            snapshotCount:
                mission
                    ?.snapshotCount ??
                status
                    ?.total ??
                status
                    ?.total_frames ??
                status
                    ?.frame_count ??
                null,

            profile:
                mission
                    ?.profile ??
                status
                    ?.profile ??
                null,

            startedAt:
                mission
                    ?.startedAt ??
                status
                    ?.started_at ??
                status
                    ?.startedAt ??
                null,

            endedAt:
                mission
                    ?.endedAt ??
                status
                    ?.ended_at ??
                status
                    ?.endedAt ??
                null,

            durationMs:
                mission
                    ?.durationMs ??
                (
                    elapsedSeconds !==
                    null
                        ? elapsedSeconds *
                          1000
                        : null
                )
        };
    }

    function normalizeFaultClassification(
        classification
    ) {
        if (!classification) {
            return null;
        }

        if (
            classification
                .primaryFault
        ) {
            return classification;
        }

        const faultId =
            classification
                .faultId ??
            classification
                .primaryFaultId ??
            null;

        const faultName =
            classification
                .faultName ??
            classification
                .label ??
            classification
                .name ??
            null;

        const confidence =
            number(
                classification
                    .confidence,
                null
            );

        const primaryFault =
            (
                faultId ||
                faultName
            )
                ? {
                    id:
                        faultId,

                    label:
                        faultName ||
                        faultId,

                    subsystem:
                        classification
                            .subsystem ??
                        null,

                    component:
                        classification
                            .affectedComponent ??
                        classification
                            .component ??
                        null,

                    confidence,

                    evidence:
                        Array.isArray(
                            classification
                                .evidence
                        )
                            ? classification
                                .evidence
                            : []
                }
                : null;

        const ranked =
            Array.isArray(
                classification
                    .rankedFaults
            )
                ? classification
                    .rankedFaults
                : Array.isArray(
                    classification
                        .alternatives
                )
                    ? classification
                        .alternatives
                    : [];

        const alternatives =
            ranked
                .filter(
                    item => {
                        const id =
                            item
                                ?.faultId ??
                            item
                                ?.id ??
                            null;

                        const label =
                            item
                                ?.faultName ??
                            item
                                ?.label ??
                            item
                                ?.name ??
                            null;

                        if (
                            !primaryFault
                        ) {
                            return true;
                        }

                        if (
                            id &&
                            primaryFault
                                .id &&
                            id ===
                            primaryFault
                                .id
                        ) {
                            return false;
                        }

                        if (
                            label &&
                            primaryFault
                                .label &&
                            label ===
                            primaryFault
                                .label
                        ) {
                            return false;
                        }

                        return true;
                    }
                )
                .map(
                    item => ({
                        id:
                            item
                                ?.faultId ??
                            item
                                ?.id ??
                            null,

                        label:
                            item
                                ?.faultName ??
                            item
                                ?.label ??
                            item
                                ?.name ??
                            "Unknown fault",

                        confidence:
                            number(
                                item
                                    ?.confidence ??
                                item
                                    ?.score,
                                0
                            ),

                        subsystem:
                            item
                                ?.subsystem ??
                            null,

                        component:
                            item
                                ?.affectedComponent ??
                            item
                                ?.component ??
                            null
                    })
                );

        return {
            ...classification,
            primaryFault,
            alternatives
        };
    }

    function buildSummaryFallback(
        {
            anomaly,
            degradation,
            rul,
            maintenance,
            missionIntelligence
        }
    ) {
        return {
            maximumAnomaly:
                number(
                    anomaly
                        ?.anomalyScore,
                    null
                ),

            maximumDegradation:
                number(
                    degradation
                        ?.overallDegradation,
                    null
                ),

            minimumRUL:
                number(
                    rul
                        ?.overallRULHours,
                    null
                ),

            finalReadiness:
                missionIntelligence
                    ?.readiness ??
                null,

            highestMaintenancePriority:
                maintenance
                    ?.priority ??
                null,

            maximumMissionRisk:
                number(
                    missionIntelligence
                        ?.missionRisk,
                    null
                ),

            derivedFromCurrentState:
                true
        };
    }

    function collectReportData() {
        const mission =
            getMissionReplay();

        const health =
            getModuleLatest(
                "PRATIRUP_HEALTH"
            ) ||
            getModuleLatest(
                "PratirupHealthMonitor"
            );

        const faultAnalysis =
            getModuleLatest(
                "PratirupFaultDetection"
            );

        const anomaly =
            getModuleLatest(
                "PratirupAnomalyDetection"
            );

        const classification =
            normalizeFaultClassification(
                getModuleLatest(
                    "PratirupFaultClassifier"
                )
            );

        const degradation =
            getModuleLatest(
                "PratirupDegradationTracker"
            );

        const rul =
            getModuleLatest(
                "PratirupRULEngine"
            );

        const maintenance =
            getModuleLatest(
                "PratirupPredictiveMaintenance"
            );

        const missionIntelligence =
            getModuleLatest(
                "PratirupMissionIntelligence"
            );

        let legacySummary =
            null;

        try {
            legacySummary =
                window
                    .PratirupMissionReplay
                    ?.getSummary?.() ||
                null;
        }
        catch (_) {}

        const summary =
            mission?.summary ||
            legacySummary ||
            buildSummaryFallback({
                anomaly,
                degradation,
                rul,
                maintenance,
                missionIntelligence
            });

        return {
            generatedAt:
                Date.now(),

            mission,

            missionSummary:
                summary,

            health,

            faultAnalysis,

            anomaly,

            classification,

            degradation,

            rul,

            maintenance,

            missionIntelligence
        };
    }

    function buildReportHeader(
        data
    ) {
        return `
            <header class="pratirup-report-header">
                <div class="report-brand">
                    <img
                        src="${CONFIG.logoPath}"
                        alt="PRATIRUP Logo"
                        class="report-logo"
                    />

                    <div class="report-brand-copy">
                        <h1>
                            ${CONFIG.reportTitle}
                        </h1>

                        <h2>
                            ${CONFIG.reportSubtitle}
                        </h2>

                        <p>
                            ${CONFIG.classification}
                        </p>
                    </div>
                </div>

                <div class="report-generated">
                    <span>
                        GENERATED
                    </span>

                    <strong>
                        ${escapeHTML(
                            formatDateTime(
                                data
                                    .generatedAt
                            )
                        )}
                    </strong>
                </div>
            </header>
        `;
    }

    function sectionHeader(
        index,
        kicker,
        title
    ) {
        return `
            <div class="report-section-heading">
                <div class="section-number">
                    ${String(
                        index
                    ).padStart(
                        2,
                        "0"
                    )}
                </div>

                <div>
                    <small>
                        ${escapeHTML(
                            kicker
                        )}
                    </small>

                    <h3>
                        ${escapeHTML(
                            title
                        )}
                    </h3>
                </div>
            </div>
        `;
    }

    function metric(
        label,
        value,
        unit = ""
    ) {
        return `
            <div class="report-metric">
                <span>
                    ${escapeHTML(
                        label
                    )}
                </span>

                <strong>
                    ${escapeHTML(
                        value
                    )}
                    ${
                        unit
                            ? `<small>${escapeHTML(
                                unit
                            )}</small>`
                            : ""
                    }
                </strong>
            </div>
        `;
    }

    function dataRow(
        label,
        value
    ) {
        return `
            <div class="report-data-row">
                <span>
                    ${escapeHTML(
                        label
                    )}
                </span>

                <strong>
                    ${escapeHTML(
                        value
                    )}
                </strong>
            </div>
        `;
    }

    function buildMissionInformation(
        data
    ) {
        const mission =
            data.mission;

        const config =
            data
                .missionIntelligence
                ?.configuration ||
            {};

        return `
            <section class="report-section">
                ${sectionHeader(
                    1,
                    "MISSION IDENTIFICATION",
                    "Mission Information"
                )}

                <div class="report-grid report-grid-4">
                    ${metric(
                        "Mission ID",
                        text(
                            mission
                                ?.id
                        )
                    )}

                    ${metric(
                        "Mission Name",
                        text(
                            mission
                                ?.name,
                            "PRATIRUP Mission"
                        )
                    )}

                    ${metric(
                        "Profile",
                        text(
                            mission
                                ?.profile ||
                            config
                                .profile
                        )
                    )}

                    ${metric(
                        "Duration",
                        mission
                            ?.durationMs !==
                            null &&
                        mission
                            ?.durationMs !==
                            undefined
                            ? formatDuration(
                                mission
                                    .durationMs
                            )
                            : "--"
                    )}
                </div>

                <div class="report-data-block">
                    ${dataRow(
                        "Mission Start",
                        formatDateTime(
                            mission
                                ?.startedAt
                        )
                    )}

                    ${dataRow(
                        "Mission End",
                        formatDateTime(
                            mission
                                ?.endedAt
                        )
                    )}

                    ${dataRow(
                        "Snapshots Recorded",
                        text(
                            mission
                                ?.snapshotCount,
                            "--"
                        )
                    )}

                    ${dataRow(
                        "Configured Altitude",
                        config
                            .altitudeFt !==
                        undefined
                            ? `${round(
                                config
                                    .altitudeFt,
                                0
                            )} ft`
                            : "--"
                    )}

                    ${dataRow(
                        "Ambient Temperature",
                        config
                            .ambientTemperatureC !==
                        undefined
                            ? `${round(
                                config
                                    .ambientTemperatureC,
                                1
                            )} °C`
                            : "--"
                    )}

                    ${dataRow(
                        "Expected Load",
                        config
                            .expectedLoadPercent !==
                        undefined
                            ? `${round(
                                config
                                    .expectedLoadPercent,
                                1
                            )}%`
                            : "--"
                    )}
                </div>
            </section>
        `;
    }

    function buildMissionSummary(
        data
    ) {
        const summary =
            data
                .missionSummary ||
            {};

        return `
            <section class="report-section">
                ${sectionHeader(
                    2,
                    "POST-FLIGHT OVERVIEW",
                    "Mission Summary"
                )}

                <div class="report-grid report-grid-4">
                    ${metric(
                        "Maximum Anomaly",
                        summary
                            .maximumAnomaly !==
                        undefined &&
                        summary
                            .maximumAnomaly !==
                        null
                            ? `${round(
                                summary
                                    .maximumAnomaly
                            )}%`
                            : "--"
                    )}

                    ${metric(
                        "Maximum Degradation",
                        summary
                            .maximumDegradation !==
                        undefined &&
                        summary
                            .maximumDegradation !==
                        null
                            ? `${round(
                                summary
                                    .maximumDegradation
                            )}%`
                            : "--"
                    )}

                    ${metric(
                        "Minimum RUL",
                        summary
                            .minimumRUL !==
                        null &&
                        summary
                            .minimumRUL !==
                        undefined
                            ? `${round(
                                summary
                                    .minimumRUL
                            )} h`
                            : "--"
                    )}

                    ${metric(
                        "Final Readiness",
                        text(
                            summary
                                .finalReadiness
                        )
                    )}
                </div>

                <div class="report-data-block">
                    ${dataRow(
                        "Highest Maintenance Priority",
                        text(
                            summary
                                .highestMaintenancePriority
                        )
                    )}

                    ${dataRow(
                        "Maximum Mission Risk",
                        summary
                            .maximumMissionRisk !==
                        undefined &&
                        summary
                            .maximumMissionRisk !==
                        null
                            ? `${round(
                                summary
                                    .maximumMissionRisk
                            )}%`
                            : "--"
                    )}
                </div>
            </section>
        `;
    }

    function buildHealthReport(
        data
    ) {
        const health =
            data.health;

        const subsystems =
            health
                ?.subsystems ||
            {};

        return `
            <section class="report-section">
                ${sectionHeader(
                    3,
                    "ENGINE CONDITION",
                    "Engine Health Report"
                )}

                <div class="report-grid report-grid-3">
                    ${metric(
                        "Overall Health",
                        health
                            ?.overallIndex !==
                        undefined &&
                        health
                            ?.overallIndex !==
                        null
                            ? `${round(
                                health
                                    .overallIndex
                            )}%`
                            : "--"
                    )}

                    ${metric(
                        "Health Status",
                        text(
                            health
                                ?.status
                        )
                    )}

                    ${metric(
                        "Data Coverage",
                        health
                            ?.coverage
                            ?.fraction !==
                        undefined &&
                        health
                            ?.coverage
                            ?.fraction !==
                        null
                            ? `${round(
                                health
                                    .coverage
                                    .fraction *
                                100
                            )}%`
                            : "--"
                    )}
                </div>

                <div class="report-data-block">
                    ${dataRow(
                        "Thermal",
                        subsystems
                            .thermal
                            ?.score !==
                        undefined &&
                        subsystems
                            .thermal
                            ?.score !==
                        null
                            ? `${round(
                                subsystems
                                    .thermal
                                    .score
                            )}%`
                            : "--"
                    )}

                    ${dataRow(
                        "Combustion",
                        subsystems
                            .combustion
                            ?.score !==
                        undefined &&
                        subsystems
                            .combustion
                            ?.score !==
                        null
                            ? `${round(
                                subsystems
                                    .combustion
                                    .score
                            )}%`
                            : "--"
                    )}

                    ${dataRow(
                        "Lubrication",
                        subsystems
                            .lubrication
                            ?.score !==
                        undefined &&
                        subsystems
                            .lubrication
                            ?.score !==
                        null
                            ? `${round(
                                subsystems
                                    .lubrication
                                    .score
                            )}%`
                            : "--"
                    )}

                    ${dataRow(
                        "Fuel System",
                        subsystems
                            .fuelSystem
                            ?.score !==
                        undefined &&
                        subsystems
                            .fuelSystem
                            ?.score !==
                        null
                            ? `${round(
                                subsystems
                                    .fuelSystem
                                    .score
                            )}%`
                            : "--"
                    )}

                    ${dataRow(
                        "Mechanical",
                        subsystems
                            .mechanical
                            ?.score !==
                        undefined &&
                        subsystems
                            .mechanical
                            ?.score !==
                        null
                            ? `${round(
                                subsystems
                                    .mechanical
                                    .score
                            )}%`
                            : "--"
                    )}
                </div>
            </section>
        `;
    }

    function buildFaultReport(
        data
    ) {
        const fault =
            data
                .classification
                ?.primaryFault;

        const alternatives =
            data
                .classification
                ?.alternatives ||
            [];

        const evidence =
            fault
                ?.evidence ||
            [];

        return `
            <section class="report-section">
                ${sectionHeader(
                    4,
                    "DIAGNOSTIC INTELLIGENCE",
                    "Fault & Anomaly Report"
                )}

                <div class="report-grid report-grid-4">
                    ${metric(
                        "Anomaly Score",
                        data
                            .anomaly
                            ?.anomalyScore !==
                        undefined &&
                        data
                            .anomaly
                            ?.anomalyScore !==
                        null
                            ? `${round(
                                data
                                    .anomaly
                                    .anomalyScore
                            )}%`
                            : "--"
                    )}

                    ${metric(
                        "Most Probable Fault",
                        text(
                            fault
                                ?.label,
                            "NONE"
                        )
                    )}

                    ${metric(
                        "Fault Confidence",
                        fault
                            ?.confidence !==
                        undefined &&
                        fault
                            ?.confidence !==
                        null
                            ? `${round(
                                fault
                                    .confidence
                            )}%`
                            : "--"
                    )}

                    ${metric(
                        "Active Faults",
                        text(
                            data
                                .faultAnalysis
                                ?.activeFaultCount,
                            "0"
                        )
                    )}
                </div>

                <div class="report-data-block">
                    ${dataRow(
                        "Affected Subsystem",
                        text(
                            fault
                                ?.subsystem
                        )
                    )}

                    ${dataRow(
                        "Affected Component",
                        text(
                            fault
                                ?.component
                        )
                    )}

                    ${dataRow(
                        "Classifier Status",
                        text(
                            data
                                .classification
                                ?.status
                        )
                    )}

                    ${dataRow(
                        "Diagnostic Explanation",
                        text(
                            data
                                .classification
                                ?.explanation
                        )
                    )}
                </div>

                <div class="report-subsection">
                    <h4>
                        Supporting Evidence
                    </h4>

                    <ul>
                        ${
                            evidence.length
                                ? evidence
                                    .map(
                                        item =>
                                            `<li>${escapeHTML(
                                                item
                                            )}</li>`
                                    )
                                    .join("")
                                : "<li>No significant supporting evidence recorded.</li>"
                        }
                    </ul>
                </div>

                <div class="report-subsection">
                    <h4>
                        Alternative Candidates
                    </h4>

                    <div class="candidate-list">
                        ${
                            alternatives.length
                                ? alternatives
                                    .slice(
                                        0,
                                        3
                                    )
                                    .map(
                                        item => `
                                            <div>
                                                <span>
                                                    ${escapeHTML(
                                                        item.label
                                                    )}
                                                </span>

                                                <strong>
                                                    ${round(
                                                        item.confidence
                                                    )}%
                                                </strong>
                                            </div>
                                        `
                                    )
                                    .join("")
                                : `
                                    <div>
                                        <span>
                                            No alternative fault candidate
                                        </span>
                                        <strong>--</strong>
                                    </div>
                                `
                        }
                    </div>
                </div>
            </section>
        `;
    }

    function buildDegradationReport(
        data
    ) {
        const degradation =
            data
                .degradation;

        const subsystems =
            degradation
                ?.subsystems ||
            {};

        return `
            <section class="report-section">
                ${sectionHeader(
                    5,
                    "TREND MONITORING",
                    "Degradation Report"
                )}

                <div class="report-grid report-grid-3">
                    ${metric(
                        "Overall Degradation",
                        degradation
                            ?.overallDegradation !==
                        undefined &&
                        degradation
                            ?.overallDegradation !==
                        null
                            ? `${round(
                                degradation
                                    .overallDegradation
                            )}%`
                            : "--"
                    )}

                    ${metric(
                        "Overall Health",
                        degradation
                            ?.overallHealth !==
                        undefined &&
                        degradation
                            ?.overallHealth !==
                        null
                            ? `${round(
                                degradation
                                    .overallHealth
                            )}%`
                            : "--"
                    )}

                    ${metric(
                        "Dominant Subsystem",
                        text(
                            degradation
                                ?.dominantSubsystem
                                ?.name
                        )
                    )}
                </div>

                <div class="report-table-wrap">
                    <table class="report-table">
                        <thead>
                            <tr>
                                <th>Subsystem</th>
                                <th>Degradation</th>
                                <th>Rate</th>
                                <th>Persistence</th>
                                <th>Trend</th>
                                <th>Level</th>
                            </tr>
                        </thead>

                        <tbody>
                            ${
                                Object.entries(
                                    subsystems
                                )
                                    .map(
                                        (
                                            [
                                                name,
                                                item
                                            ]
                                        ) => `
                                            <tr>
                                                <td>
                                                    ${escapeHTML(
                                                        name
                                                    )}
                                                </td>

                                                <td>
                                                    ${round(
                                                        item
                                                            .degradation
                                                    )}%
                                                </td>

                                                <td>
                                                    ${round(
                                                        item
                                                            .degradationRate,
                                                        3
                                                    )}
                                                </td>

                                                <td>
                                                    ${round(
                                                        item
                                                            .persistence
                                                    )}%
                                                </td>

                                                <td>
                                                    ${escapeHTML(
                                                        text(
                                                            item
                                                                .trend
                                                        )
                                                    )}
                                                </td>

                                                <td>
                                                    ${escapeHTML(
                                                        text(
                                                            item
                                                                .level
                                                        )
                                                    )}
                                                </td>
                                            </tr>
                                        `
                                    )
                                    .join("")
                            }
                        </tbody>
                    </table>
                </div>
            </section>
        `;
    }

    function buildRULReport(
        data
    ) {
        const rul =
            data.rul;

        const subsystems =
            rul
                ?.subsystems ||
            {};

        return `
            <section class="report-section">
                ${sectionHeader(
                    6,
                    "PROGNOSTICS",
                    "Remaining Useful Life"
                )}

                <div class="report-grid report-grid-4">
                    ${metric(
                        "Overall RUL",
                        rul
                            ?.overallRULHours !==
                        undefined &&
                        rul
                            ?.overallRULHours !==
                        null
                            ? `${round(
                                rul
                                    .overallRULHours
                            )} h`
                            : "--"
                    )}

                    ${metric(
                        "RUL Status",
                        text(
                            rul
                                ?.status
                        )
                    )}

                    ${metric(
                        "Confidence",
                        rul
                            ?.confidence !==
                        undefined &&
                        rul
                            ?.confidence !==
                        null
                            ? `${round(
                                rul
                                    .confidence
                            )}%`
                            : "--"
                    )}

                    ${metric(
                        "Critical Subsystem",
                        text(
                            rul
                                ?.criticalSubsystem
                                ?.name
                        )
                    )}
                </div>

                <div class="report-table-wrap">
                    <table class="report-table">
                        <thead>
                            <tr>
                                <th>Subsystem</th>
                                <th>RUL</th>
                                <th>Remaining Life</th>
                                <th>Confidence</th>
                                <th>Status</th>
                                <th>Trend</th>
                            </tr>
                        </thead>

                        <tbody>
                            ${
                                Object.entries(
                                    subsystems
                                )
                                    .map(
                                        (
                                            [
                                                name,
                                                item
                                            ]
                                        ) => `
                                            <tr>
                                                <td>
                                                    ${escapeHTML(
                                                        name
                                                    )}
                                                </td>

                                                <td>
                                                    ${round(
                                                        item
                                                            .rulHours
                                                    )} h
                                                </td>

                                                <td>
                                                    ${round(
                                                        item
                                                            .remainingLifePercent
                                                    )}%
                                                </td>

                                                <td>
                                                    ${round(
                                                        item
                                                            .confidence
                                                    )}%
                                                </td>

                                                <td>
                                                    ${escapeHTML(
                                                        text(
                                                            item
                                                                .status
                                                        )
                                                    )}
                                                </td>

                                                <td>
                                                    ${escapeHTML(
                                                        text(
                                                            item
                                                                .trend
                                                        )
                                                    )}
                                                </td>
                                            </tr>
                                        `
                                    )
                                    .join("")
                            }
                        </tbody>
                    </table>
                </div>

                <div class="prototype-note">
                    Prototype RUL estimate only.
                    Final RUL must be calibrated using
                    validated engine/test-rig and historical
                    degradation data.
                </div>
            </section>
        `;
    }

    function buildMaintenanceReport(
        data
    ) {
        const maintenance =
            data
                .maintenance;

        const primaryFault =
            data
                .classification
                ?.primaryFault;

        return `
            <section class="report-section">
                ${sectionHeader(
                    7,
                    "MAINTENANCE INTELLIGENCE",
                    "Predictive Maintenance"
                )}

                <div class="report-grid report-grid-4">
                    ${metric(
                        "Priority",
                        text(
                            maintenance
                                ?.priority
                        )
                    )}

                    ${metric(
                        "Maintenance Risk",
                        maintenance
                            ?.maintenanceRisk !==
                        undefined &&
                        maintenance
                            ?.maintenanceRisk !==
                        null
                            ? `${round(
                                maintenance
                                    .maintenanceRisk
                            )}%`
                            : "--"
                    )}

                    ${metric(
                        "Confidence",
                        maintenance
                            ?.confidence !==
                        undefined &&
                        maintenance
                            ?.confidence !==
                        null
                            ? `${round(
                                maintenance
                                    .confidence
                            )}%`
                            : "--"
                    )}

                    ${metric(
                        "Service Window",
                        text(
                            maintenance
                                ?.serviceWindow
                                ?.code
                        )
                    )}
                </div>

                <div class="report-data-block">
                    ${dataRow(
                        "Affected Subsystem",
                        text(
                            maintenance
                                ?.affectedSubsystem ||
                            primaryFault
                                ?.subsystem
                        )
                    )}

                    ${dataRow(
                        "Affected Component",
                        text(
                            maintenance
                                ?.affectedComponent ||
                            primaryFault
                                ?.component
                        )
                    )}

                    ${dataRow(
                        "Probable Fault",
                        text(
                            maintenance
                                ?.probableFault ||
                            primaryFault
                                ?.label,
                            "NONE"
                        )
                    )}

                    ${dataRow(
                        "Inspection Recommendation",
                        text(
                            maintenance
                                ?.inspection
                        )
                    )}

                    ${dataRow(
                        "Recommended Action",
                        text(
                            maintenance
                                ?.recommendedAction
                        )
                    )}

                    ${dataRow(
                        "Mission Restriction",
                        text(
                            maintenance
                                ?.missionRestriction
                                ?.level
                        )
                    )}
                </div>

                <div class="report-advisory">
                    <small>
                        MAINTENANCE ADVISORY
                    </small>

                    <p>
                        ${escapeHTML(
                            text(
                                maintenance
                                    ?.advisory,
                                "No maintenance advisory available."
                            )
                        )}
                    </p>
                </div>
            </section>
        `;
    }

    function buildMissionReadinessReport(
        data
    ) {
        const mission =
            data
                .missionIntelligence;

        const reasons =
            mission
                ?.reasons ||
            [];

        const readinessClass =
            String(
                mission
                    ?.readiness ||
                "unknown"
            )
                .toLowerCase()
                .replaceAll(
                    "_",
                    "-"
                );

        return `
            <section class="report-section">
                ${sectionHeader(
                    8,
                    "MISSION DECISION SUPPORT",
                    "Mission Readiness"
                )}

                <div class="report-readiness ${escapeHTML(
                    readinessClass
                )}">
                    <span>
                        READINESS
                    </span>

                    <strong>
                        ${escapeHTML(
                            text(
                                mission
                                    ?.readiness
                            )
                        )}
                    </strong>
                </div>

                <div class="report-grid report-grid-4">
                    ${metric(
                        "Mission Risk",
                        mission
                            ?.missionRisk !==
                        undefined &&
                        mission
                            ?.missionRisk !==
                        null
                            ? `${round(
                                mission
                                    .missionRisk
                            )}%`
                            : "--"
                    )}

                    ${metric(
                        "Propulsion Risk",
                        mission
                            ?.propulsionHealthRisk !==
                        undefined &&
                        mission
                            ?.propulsionHealthRisk !==
                        null
                            ? `${round(
                                mission
                                    .propulsionHealthRisk
                            )}%`
                            : "--"
                    )}

                    ${metric(
                        "Environmental Risk",
                        mission
                            ?.environmentalRisk !==
                        undefined &&
                        mission
                            ?.environmentalRisk !==
                        null
                            ? `${round(
                                mission
                                    .environmentalRisk
                            )}%`
                            : "--"
                    )}

                    ${metric(
                        "RUL Margin",
                        mission
                            ?.rulMargin
                            ?.marginHours !==
                        undefined &&
                        mission
                            ?.rulMargin
                            ?.marginHours !==
                        null
                            ? `${round(
                                mission
                                    .rulMargin
                                    .marginHours
                            )} h`
                            : "--"
                    )}
                </div>

                <div class="report-subsection">
                    <h4>
                        Risk Reasons
                    </h4>

                    <ul>
                        ${
                            reasons.length
                                ? reasons
                                    .map(
                                        reason =>
                                            `<li>${escapeHTML(
                                                reason
                                            )}</li>`
                                    )
                                    .join("")
                                : "<li>No mission risk explanation available.</li>"
                        }
                    </ul>
                </div>

                <div class="report-advisory">
                    <small>
                        MISSION RECOMMENDATION
                    </small>

                    <p>
                        ${escapeHTML(
                            text(
                                mission
                                    ?.recommendation
                            )
                        )}
                    </p>
                </div>

                <div class="prototype-note">
                    This is prototype mission decision support
                    and is not a flight authorization.
                </div>
            </section>
        `;
    }

    function getSnapshotPrimaryFault(
        snapshot
    ) {
        const classification =
            normalizeFaultClassification(
                snapshot
                    ?.classification
            );

        return classification
            ?.primaryFault ||
            null;
    }

    function buildTimeline(
        data
    ) {
        const snapshots =
            data
                .mission
                ?.snapshots ||
            [];

        const significant =
            snapshots
                .filter(
                    snapshot => {
                        const anomaly =
                            number(
                                snapshot
                                    ?.anomaly
                                    ?.anomalyScore,
                                0
                            );

                        const faultCount =
                            number(
                                snapshot
                                    ?.faults
                                    ?.activeFaultCount,
                                0
                            );

                        const fault =
                            getSnapshotPrimaryFault(
                                snapshot
                            );

                        const risk =
                            number(
                                snapshot
                                    ?.missionIntelligence
                                    ?.missionRisk,
                                0
                            );

                        return (
                            anomaly >=
                            40 ||
                            faultCount >
                            0 ||
                            Boolean(
                                fault
                            ) ||
                            risk >=
                            40
                        );
                    }
                )
                .slice(
                    0,
                    50
                );

        return `
            <section class="report-section">
                ${sectionHeader(
                    9,
                    "TEMPORAL ANALYSIS",
                    "Mission Event Timeline"
                )}

                <div class="timeline-list">
                    ${
                        significant.length
                            ? significant
                                .map(
                                    snapshot => {
                                        const elapsed =
                                            (
                                                number(
                                                    snapshot
                                                        ?.elapsedMs,
                                                    0
                                                ) /
                                                1000
                                            )
                                                .toFixed(
                                                    1
                                                );

                                        const fault =
                                            getSnapshotPrimaryFault(
                                                snapshot
                                            );

                                        return `
                                            <div class="timeline-item">
                                                <div class="timeline-time">
                                                    +${elapsed}s
                                                </div>

                                                <div class="timeline-body">
                                                    <strong>
                                                        ${escapeHTML(
                                                            fault
                                                                ?.label ||
                                                            snapshot
                                                                ?.anomaly
                                                                ?.status ||
                                                            "Engine Event"
                                                        )}
                                                    </strong>

                                                    <span>
                                                        Anomaly:
                                                        ${round(
                                                            snapshot
                                                                ?.anomaly
                                                                ?.anomalyScore,
                                                            1
                                                        )}%
                                                        •
                                                        Mission Risk:
                                                        ${round(
                                                            snapshot
                                                                ?.missionIntelligence
                                                                ?.missionRisk,
                                                            1
                                                        )}%
                                                    </span>
                                                </div>
                                            </div>
                                        `;
                                    }
                                )
                                .join("")
                            : `
                                <div class="timeline-empty">
                                    No significant anomaly or fault event
                                    was recorded in the available mission data.
                                </div>
                            `
                    }
                </div>
            </section>
        `;
    }

    function buildFinalAssessment(
        data
    ) {
        const health =
            data
                .degradation
                ?.overallHealth;

        const fault =
            data
                .classification
                ?.primaryFault
                ?.label;

        const rul =
            data
                .rul
                ?.overallRULHours;

        const maintenance =
            data
                .maintenance;

        const readiness =
            data
                .missionIntelligence
                ?.readiness;

        let assessment =
            "";

        if (
            readiness ===
            "NO-GO"
        ) {
            assessment =
                "The prototype Digital Twin indicates a significant propulsion-health or mission-risk concern. Engineering inspection is recommended before committing to a comparable mission profile.";
        }
        else if (
            readiness ===
            "CAUTION"
        ) {
            assessment =
                "The engine remains operational in the prototype model, but reduced health or prognostic margin has been detected. Enhanced monitoring and engineering review are recommended.";
        }
        else if (
            readiness ===
            "GO"
        ) {
            assessment =
                "The available Digital Twin indicators show no major mission-limiting propulsion condition. Continue normal monitoring and trend analysis.";
        }
        else {
            assessment =
                "Mission-readiness information is currently unavailable or incomplete. Review the latest propulsion-health, anomaly, degradation and RUL outputs before interpreting this report.";
        }

        return `
            <section class="report-section final-assessment">
                ${sectionHeader(
                    10,
                    "ENGINEERING SUMMARY",
                    "Final Engine Assessment"
                )}

                <div class="report-grid report-grid-4">
                    ${metric(
                        "Engine Health",
                        health !==
                        undefined &&
                        health !==
                        null
                            ? `${round(
                                health
                            )}%`
                            : "--"
                    )}

                    ${metric(
                        "Primary Fault",
                        text(
                            fault,
                            "NONE"
                        )
                    )}

                    ${metric(
                        "Overall RUL",
                        rul !==
                        undefined &&
                        rul !==
                        null
                            ? `${round(
                                rul
                            )} h`
                            : "--"
                    )}

                    ${metric(
                        "Maintenance Priority",
                        text(
                            maintenance
                                ?.priority
                        )
                    )}
                </div>

                <div class="assessment-text">
                    <p>
                        ${escapeHTML(
                            assessment
                        )}
                    </p>
                </div>
            </section>
        `;
    }

    function buildReportFooter() {
        return `
            <footer class="pratirup-report-footer">
                <div class="footer-line"></div>

                <div class="footer-branding">
                    <span>
                        ${CONFIG.footerLeft}
                    </span>

                    <span class="footer-separator">
                        •
                    </span>

                    <span>
                        ${CONFIG.footerRight}
                    </span>
                </div>

                <small>
                    PRATIRUP • PS 26054 • DIGITAL TWIN MISSION REPORT
                </small>
            </footer>
        `;
    }

    function buildReportStyles() {
        return `
<style>

:root {
    --report-bg:
        #05090f;

    --report-panel:
        #0b131c;

    --report-panel-2:
        #101b26;

    --report-line:
        rgba(91, 181, 255, 0.20);

    --report-cyan:
        #00d9ff;

    --report-blue:
        #007bff;

    --report-green:
        #39d698;

    --report-yellow:
        #ffbd4a;

    --report-red:
        #ff6262;

    --report-text:
        #edf7ff;

    --report-muted:
        #8295a7;
}

* {
    box-sizing:
        border-box;
}

html,
body {
    margin:
        0;

    padding:
        0;

    background:
        var(--report-bg);

    color:
        var(--report-text);

    font-family:
        Inter,
        Arial,
        sans-serif;
}

body {
    padding:
        32px;
}

.pratirup-report {
    width:
        min(
            1100px,
            100%
        );

    margin:
        0 auto;
}

.pratirup-report-header {
    display:
        flex;

    align-items:
        center;

    justify-content:
        space-between;

    gap:
        28px;

    padding:
        28px 30px;

    border:
        1px solid
        var(--report-line);

    border-radius:
        16px;

    background:
        radial-gradient(
            circle at left top,
            rgba(
                0,
                217,
                255,
                0.10
            ),
            transparent 40%
        ),
        linear-gradient(
            135deg,
            #0d1823,
            #070d13
        );

    margin-bottom:
        18px;
}

.report-brand {
    display:
        flex;

    align-items:
        center;

    gap:
        24px;
}

.report-logo {
    width:
        110px;

    height:
        110px;

    object-fit:
        contain;

    filter:
        drop-shadow(
            0 0 22px
            rgba(
                0,
                217,
                255,
                0.22
            )
        );
}

.report-brand-copy h1 {
    margin:
        0;

    font-size:
        58px;

    line-height:
        0.95;

    letter-spacing:
        0.09em;
}

.report-brand-copy h2 {
    margin:
        12px 0 5px;

    color:
        var(--report-cyan);

    font-size:
        14px;

    letter-spacing:
        0.20em;
}

.report-brand-copy p {
    margin:
        0;

    color:
        var(--report-muted);

    font-size:
        9px;

    letter-spacing:
        0.12em;
}

.report-generated {
    min-width:
        170px;

    padding:
        12px;

    border:
        1px solid
        var(--report-line);

    border-radius:
        9px;

    background:
        rgba(
            255,
            255,
            255,
            0.025
        );
}

.report-generated span {
    display:
        block;

    color:
        var(--report-muted);

    font-size:
        8px;

    font-weight:
        800;

    letter-spacing:
        0.12em;
}

.report-generated strong {
    display:
        block;

    margin-top:
        6px;

    font-size:
        10px;
}

.report-section {
    margin-top:
        14px;

    border:
        1px solid
        var(--report-line);

    border-radius:
        13px;

    background:
        linear-gradient(
            180deg,
            rgba(
                15,
                25,
                35,
                0.98
            ),
            rgba(
                8,
                14,
                21,
                0.98
            )
        );

    overflow:
        hidden;
}

.report-section-heading {
    display:
        flex;

    align-items:
        center;

    gap:
        13px;

    min-height:
        62px;

    padding:
        12px 16px;

    border-bottom:
        1px solid
        var(--report-line);
}

.section-number {
    width:
        34px;

    height:
        34px;

    display:
        grid;

    place-items:
        center;

    border:
        1px solid
        rgba(
            0,
            217,
            255,
            0.35
        );

    border-radius:
        8px;

    color:
        var(--report-cyan);

    font-size:
        10px;

    font-weight:
        800;
}

.report-section-heading small {
    display:
        block;

    color:
        var(--report-cyan);

    font-size:
        7px;

    font-weight:
        800;

    letter-spacing:
        0.14em;
}

.report-section-heading h3 {
    margin:
        4px 0 0;

    font-size:
        16px;
}

.report-grid {
    display:
        grid;

    gap:
        8px;

    padding:
        14px;
}

.report-grid-3 {
    grid-template-columns:
        repeat(
            3,
            minmax(
                0,
                1fr
            )
        );
}

.report-grid-4 {
    grid-template-columns:
        repeat(
            4,
            minmax(
                0,
                1fr
            )
        );
}

.report-metric {
    padding:
        12px;

    border:
        1px solid
        rgba(
            255,
            255,
            255,
            0.06
        );

    border-radius:
        8px;

    background:
        rgba(
            255,
            255,
            255,
            0.02
        );
}

.report-metric span {
    display:
        block;

    color:
        var(--report-muted);

    font-size:
        8px;

    font-weight:
        800;

    letter-spacing:
        0.08em;
}

.report-metric strong {
    display:
        block;

    margin-top:
        7px;

    font-size:
        17px;
}

.report-metric small {
    color:
        var(--report-muted);

    font-size:
        8px;
}

.report-data-block {
    padding:
        2px 15px 15px;
}

.report-data-row {
    display:
        flex;

    justify-content:
        space-between;

    gap:
        16px;

    padding:
        9px 0;

    border-bottom:
        1px solid
        rgba(
            255,
            255,
            255,
            0.04
        );
}

.report-data-row:last-child {
    border-bottom:
        none;
}

.report-data-row span {
    color:
        var(--report-muted);

    font-size:
        9px;
}

.report-data-row strong {
    max-width:
        70%;

    text-align:
        right;

    font-size:
        9px;
}

.report-subsection {
    margin:
        0 14px 14px;

    padding:
        12px;

    border:
        1px solid
        rgba(
            255,
            255,
            255,
            0.05
        );

    border-radius:
        8px;

    background:
        rgba(
            255,
            255,
            255,
            0.018
        );
}

.report-subsection h4 {
    margin:
        0 0 9px;

    color:
        var(--report-cyan);

    font-size:
        10px;
}

.report-subsection ul {
    margin:
        0;

    padding-left:
        19px;
}

.report-subsection li {
    margin:
        5px 0;

    color:
        var(--report-muted);

    font-size:
        9px;

    line-height:
        1.5;
}

.candidate-list div {
    display:
        flex;

    justify-content:
        space-between;

    gap:
        15px;

    padding:
        6px 0;

    border-bottom:
        1px solid
        rgba(
            255,
            255,
            255,
            0.04
        );
}

.candidate-list div:last-child {
    border-bottom:
        none;
}

.candidate-list span {
    color:
        var(--report-muted);

    font-size:
        9px;
}

.candidate-list strong {
    font-size:
        9px;
}

.report-table-wrap {
    padding:
        0 14px 14px;

    overflow-x:
        auto;
}

.report-table {
    width:
        100%;

    border-collapse:
        collapse;
}

.report-table th,
.report-table td {
    padding:
        8px;

    border:
        1px solid
        rgba(
            255,
            255,
            255,
            0.06
        );

    text-align:
        left;

    font-size:
        8px;
}

.report-table th {
    color:
        var(--report-cyan);

    background:
        rgba(
            0,
            217,
            255,
            0.045
        );
}

.report-table td {
    color:
        #c4d1dc;
}

.report-advisory {
    margin:
        0 14px 14px;

    padding:
        13px;

    border:
        1px solid
        rgba(
            0,
            217,
            255,
            0.17
        );

    border-radius:
        8px;

    background:
        rgba(
            0,
            217,
            255,
            0.035
        );
}

.report-advisory small {
    color:
        var(--report-cyan);

    font-size:
        7px;

    font-weight:
        800;

    letter-spacing:
        0.11em;
}

.report-advisory p {
    margin:
        7px 0 0;

    color:
        var(--report-muted);

    font-size:
        9px;

    line-height:
        1.6;
}

.report-readiness {
    margin:
        14px;

    padding:
        16px;

    border-radius:
        9px;

    border:
        1px solid
        var(--report-line);
}

.report-readiness span {
    display:
        block;

    color:
        var(--report-muted);

    font-size:
        8px;

    font-weight:
        800;
}

.report-readiness strong {
    display:
        block;

    margin-top:
        7px;

    font-size:
        28px;
}

.report-readiness.go strong {
    color:
        var(--report-green);
}

.report-readiness.caution strong {
    color:
        var(--report-yellow);
}

.report-readiness.no-go strong {
    color:
        var(--report-red);
}

.timeline-list {
    padding:
        14px;
}

.timeline-item {
    display:
        grid;

    grid-template-columns:
        90px 1fr;

    gap:
        12px;

    padding:
        10px;

    border-bottom:
        1px solid
        rgba(
            255,
            255,
            255,
            0.05
        );
}

.timeline-time {
    color:
        var(--report-cyan);

    font-size:
        9px;

    font-weight:
        800;
}

.timeline-body strong {
    display:
        block;

    font-size:
        9px;
}

.timeline-body span {
    display:
        block;

    margin-top:
        4px;

    color:
        var(--report-muted);

    font-size:
        8px;
}

.timeline-empty {
    padding:
        25px;

    color:
        var(--report-muted);

    text-align:
        center;

    font-size:
        9px;
}

.assessment-text {
    padding:
        0 15px 16px;
}

.assessment-text p {
    margin:
        0;

    color:
        #cbd8e2;

    font-size:
        10px;

    line-height:
        1.7;
}

.prototype-note {
    margin:
        0 14px 14px;

    padding:
        9px 11px;

    border-left:
        3px solid
        var(--report-yellow);

    color:
        var(--report-muted);

    background:
        rgba(
            255,
            189,
            74,
            0.04
        );

    font-size:
        8px;

    line-height:
        1.5;
}

.pratirup-report-footer {
    margin-top:
        24px;

    padding:
        22px 10px;

    text-align:
        center;
}

.footer-line {
    height:
        1px;

    margin-bottom:
        16px;

    background:
        linear-gradient(
            90deg,
            transparent,
            var(--report-cyan),
            transparent
        );
}

.footer-branding {
    display:
        flex;

    justify-content:
        center;

    align-items:
        center;

    gap:
        11px;

    font-size:
        12px;

    font-weight:
        800;

    letter-spacing:
        0.12em;
}

.footer-branding span:first-child {
    color:
        var(--report-cyan);
}

.footer-branding span:last-child {
    color:
        #7ca8ff;
}

.footer-separator {
    color:
        var(--report-muted) !important;
}

.pratirup-report-footer small {
    display:
        block;

    margin-top:
        9px;

    color:
        var(--report-muted);

    font-size:
        7px;

    letter-spacing:
        0.1em;
}

@media print {
    body {
        background:
            white;

        color:
            #111;

        padding:
            0;
    }

    .pratirup-report {
        width:
            100%;
    }

    .pratirup-report-header,
    .report-section {
        box-shadow:
            none;

        break-inside:
            avoid;
    }

    .report-section {
        page-break-inside:
            avoid;
    }
}

@media (
    max-width: 800px
) {
    body {
        padding:
            12px;
    }

    .pratirup-report-header {
        flex-direction:
            column;

        align-items:
            flex-start;
    }

    .report-brand {
        flex-direction:
            column;

        align-items:
            flex-start;
    }

    .report-brand-copy h1 {
        font-size:
            38px;
    }

    .report-grid-3,
    .report-grid-4 {
        grid-template-columns:
            1fr 1fr;
    }
}

@media (
    max-width: 500px
) {
    .report-grid-3,
    .report-grid-4 {
        grid-template-columns:
            1fr;
    }

    .report-data-row {
        flex-direction:
            column;
    }

    .report-data-row strong {
        max-width:
            100%;

        text-align:
            left;
    }
}

</style>
        `;
    }

    function buildReport(
        dataInput = null
    ) {
        const data =
            dataInput ||
            collectReportData();

        const body = `
            <div class="pratirup-report">
                ${buildReportHeader(
                    data
                )}

                ${buildMissionInformation(
                    data
                )}

                ${buildMissionSummary(
                    data
                )}

                ${buildHealthReport(
                    data
                )}

                ${buildFaultReport(
                    data
                )}

                ${buildDegradationReport(
                    data
                )}

                ${buildRULReport(
                    data
                )}

                ${buildMaintenanceReport(
                    data
                )}

                ${buildMissionReadinessReport(
                    data
                )}

                ${buildTimeline(
                    data
                )}

                ${buildFinalAssessment(
                    data
                )}

                ${buildReportFooter()}
            </div>
        `;

        latestReport = {
            timestamp:
                Date.now(),

            data:
                clone(
                    data
                ),

            html:
                body
        };

        return latestReport;
    }

    function buildDocument(
        dataInput = null
    ) {
        const report =
            buildReport(
                dataInput
            );

        return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>
        PRATIRUP Mission Report
    </title>

    ${buildReportStyles()}
</head>

<body>
    ${report.html}
</body>
</html>
        `;
    }

    function openReport(
        dataInput = null
    ) {
        const documentHTML =
            buildDocument(
                dataInput
            );

        const reportWindow =
            window.open(
                "",
                "_blank"
            );

        if (!reportWindow) {
            console.warn(
                "[PRATIRUP Report] Popup blocked."
            );

            return false;
        }

        reportWindow
            .document
            .open();

        reportWindow
            .document
            .write(
                documentHTML
            );

        reportWindow
            .document
            .close();

        return true;
    }

    function printReport(
        dataInput = null
    ) {
        const documentHTML =
            buildDocument(
                dataInput
            );

        const reportWindow =
            window.open(
                "",
                "_blank"
            );

        if (!reportWindow) {
            return false;
        }

        reportWindow
            .document
            .open();

        reportWindow
            .document
            .write(
                documentHTML
            );

        reportWindow
            .document
            .close();

        reportWindow
            .addEventListener(
                "load",
                () => {
                    setTimeout(
                        () => {
                            reportWindow
                                .focus();

                            reportWindow
                                .print();
                        },
                        250
                    );
                },
                {
                    once:
                        true
                }
            );

        return true;
    }

    function downloadHTML(
        dataInput = null
    ) {
        const documentHTML =
            buildDocument(
                dataInput
            );

        const missionId =
            dataInput
                ?.mission
                ?.id ||
            getMissionReplay()
                ?.id ||
            "PRATIRUP-MISSION";

        const safeMissionId =
            String(
                missionId
            )
                .replace(
                    /[^a-zA-Z0-9._-]/g,
                    "_"
                );

        const blob =
            new Blob(
                [
                    documentHTML
                ],
                {
                    type:
                        "text/html"
                }
            );

        const url =
            URL.createObjectURL(
                blob
            );

        const link =
            document
                .createElement(
                    "a"
                );

        link.href =
            url;

        link.download =
            `${safeMissionId}-report.html`;

        document
            .body
            .appendChild(
                link
            );

        link.click();

        link.remove();

        URL.revokeObjectURL(
            url
        );

        return true;
    }

    function exportJSON() {
        const data =
            collectReportData();

        return JSON.stringify(
            {
                format:
                    "PRATIRUP_MISSION_REPORT",

                version:
                    VERSION,

                generatedAt:
                    Date.now(),

                report:
                    data
            },
            null,
            2
        );
    }

    function connectDashboardButtons() {
        const missionButton =
            document
                .getElementById(
                    "generateMissionReport"
                );

        if (
            missionButton &&
            !missionButton
                .dataset
                .pratirupReportBound
        ) {
            missionButton
                .dataset
                .pratirupReportBound =
                "true";

            missionButton
                .addEventListener(
                    "click",
                    () => {
                        openReport();
                    }
                );
        }

        const healthButton =
            document
                .getElementById(
                    "generateHealthReport"
                );

        if (
            healthButton &&
            !healthButton
                .dataset
                .pratirupReportBound
        ) {
            healthButton
                .dataset
                .pratirupReportBound =
                "true";

            healthButton
                .addEventListener(
                    "click",
                    () => {
                        openReport();
                    }
                );
        }

        const maintenanceButton =
            document
                .getElementById(
                    "generateMaintenanceReport"
                );

        if (
            maintenanceButton &&
            !maintenanceButton
                .dataset
                .pratirupReportBound
        ) {
            maintenanceButton
                .dataset
                .pratirupReportBound =
                "true";

            maintenanceButton
                .addEventListener(
                    "click",
                    () => {
                        openReport();
                    }
                );
        }
    }

    window.PratirupMissionReportGenerator = {
        version:
            VERSION,

        collect:
            collectReportData,

        build:
            buildReport,

        buildDocument,

        open:
            openReport,

        print:
            printReport,

        downloadHTML,

        exportJSON,

        getLatest() {
            return latestReport
                ? clone(
                    latestReport
                )
                : null;
        },

        config:
            CONFIG
    };

    function initialize() {
        connectDashboardButtons();

        console.info(
            `[PRATIRUP] Mission Report Generator ${VERSION} ready.`
        );
    }

    if (
        document.readyState ===
        "loading"
    ) {
        document
            .addEventListener(
                "DOMContentLoaded",
                initialize,
                {
                    once:
                        true
                }
            );
    }
    else {
        initialize();
    }
})();

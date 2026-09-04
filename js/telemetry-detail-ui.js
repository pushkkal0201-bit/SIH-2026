(function () {

    "use strict";


    const VERSION =
        "1.0.0";


    const runtime = {

        initialized:
            false,

        listenerAttached:
            false,

        renderCount:
            0,

        eventCount:
            0,

        lastRenderedAt:
            null,

        lastError:
            null

    };


    function element(
        id
    ) {

        return document
            .getElementById(
                id
            );

    }


    function firstDefined(
        ...values
    ) {

        for (
            const value
            of values
        ) {

            if (
                value !== undefined &&
                value !== null
            ) {

                return value;

            }

        }


        return null;

    }


    function numberOrNull(
        value
    ) {

        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {

            return null;

        }


        const number =
            Number(value);


        return Number.isFinite(
            number
        )
            ? number
            : null;

    }


    function setNumericText(
        id,
        value,
        decimals
    ) {

        const node =
            element(id);


        if (!node) {

            return false;

        }


        const number =
            numberOrNull(
                value
            );


        if (
            number === null
        ) {

            node.textContent =
                "--";

            return false;

        }


        node.textContent =
            number.toFixed(
                decimals
            );


        return true;

    }


    function extractFrame(
        input
    ) {

        if (
            !input
        ) {

            return null;

        }


        if (
            typeof CustomEvent !==
                "undefined" &&
            input instanceof
                CustomEvent
        ) {

            return input.detail
                ?? null;

        }


        if (
            input.detail &&
            typeof input.detail ===
                "object"
        ) {

            return input.detail;

        }


        if (
            typeof input ===
                "object"
        ) {

            return input;

        }


        return null;

    }


    function render(
        input
    ) {

        try {

            let frame =
                extractFrame(
                    input
                );


            if (!frame) {

                frame =
                    window
                        .PRATIRUP_BRIDGE
                        ?.getTelemetry
                        ?.()
                    ??
                    null;

            }


            if (!frame) {

                return false;

            }


            const vibration =
                firstDefined(

                    frame
                        ?.vibration
                        ?.overallG,

                    frame
                        ?.vibration
                        ?.overall_g

                );


            const battery =
                firstDefined(

                    frame
                        ?.electrical
                        ?.batteryVoltageV,

                    frame
                        ?.electrical
                        ?.battery_voltage_v

                );


            const alternator =
                firstDefined(

                    frame
                        ?.electrical
                        ?.alternatorVoltageV,

                    frame
                        ?.electrical
                        ?.alternator_voltage_v

                );


            setNumericText(
                "telemetryVibration",
                vibration,
                3
            );


            setNumericText(
                "telemetryBatteryVoltage",
                battery,
                2
            );


            setNumericText(
                "telemetryAlternatorVoltage",
                alternator,
                2
            );


            runtime.renderCount +=
                1;


            runtime.lastRenderedAt =
                new Date()
                    .toISOString();


            runtime.lastError =
                null;


            return true;


        } catch (error) {

            runtime.lastError = {

                stage:
                    "RENDER",

                message:
                    String(error)

            };


            console.error(
                "[PRATIRUP TELEMETRY DETAIL UI]",
                error
            );


            return false;

        }

    }


    function handleTelemetry(
        event
    ) {

        runtime.eventCount +=
            1;


        render(
            event
        );

    }


    function initialize() {

        if (
            !runtime.listenerAttached
        ) {

            window.addEventListener(
                "pratirup:telemetry",
                handleTelemetry
            );


            runtime.listenerAttached =
                true;

        }


        runtime.initialized =
            true;


        render();


        return getStatus();

    }


    function getStatus() {

        return {

            service:
                "telemetry_detail_ui",

            version:
                VERSION,

            initialized:
                runtime.initialized,

            listener_attached:
                runtime.listenerAttached,

            render_count:
                runtime.renderCount,

            event_count:
                runtime.eventCount,

            last_rendered_at:
                runtime.lastRenderedAt,

            last_error:
                runtime.lastError

        };

    }


    window.PRATIRUPTelemetryDetailUI = {

        VERSION,

        initialize,

        render,

        getStatus

    };


    if (
        document.readyState ===
        "loading"
    ) {

        document.addEventListener(
            "DOMContentLoaded",
            initialize,
            {
                once:
                    true
            }
        );

    } else {

        initialize();

    }


    console.info(
        `[PRATIRUP] Telemetry Detail UI v${VERSION} loaded.`
    );

})();

// Completion signals must not queue behind a surface-dirty ioctl holding the
// same NVRMUserClient::fGate while waiting for the accelerator family lock.
#pragma once
#include <IOKit/IOKitLib.h>
#include <pthread.h>
#include <stdatomic.h>
#include "../kexts/NVRM/nvrm_surfshare_abi.h"
static _Atomic io_connect_t g6mf_completion_port;
static pthread_once_t g6mf_completion_once = PTHREAD_ONCE_INIT;
static _Atomic uint64_t g6mf_completion_calls, g6mf_completion_errors;
static void g6mf_completion_open(void) {
    // Same NVAccel carrier and NVRM fallback as NVK. A distinct user client has
    // its own teardown gate. Only GPU_MARK escapes ever use this connection.
    io_service_t service = IOServiceGetMatchingService(kIOMainPortDefault, IOServiceMatching("NVAccel"));
    if (service) {
        io_connect_t port = 0;
        kern_return_t kr = IOServiceOpen(service, mach_task_self(), 0x4e560000u, &port);
        IOObjectRelease(service);
        if (kr == KERN_SUCCESS) { g6mf_completion_port = port; return; }
    }
    service = IOServiceGetMatchingService(kIOMainPortDefault, IOServiceMatching("NVRM"));
    if (service) {
        io_connect_t port = 0;
        kern_return_t kr = IOServiceOpen(service, mach_task_self(), 0, &port);
        IOObjectRelease(service);
        if (kr == KERN_SUCCESS) g6mf_completion_port = port;
    }
    // No shared-channel fallback: it would reintroduce the deadlock. Returning
    // OFF to the initial probe keeps WindowServer's completion wait enabled.
    // The one successful connection lives until process exit; never close it
    // while another thread may be releasing a pending surface.
}
static uint32_t g6mf_completion_mark(uint32_t sid, int pending) {
    const char *name = getprogname();
    if (!name || strcmp(name, "WindowServer")) return NVRM_SS_OFF;
    pthread_once(&g6mf_completion_once, g6mf_completion_open);
    if (!g6mf_completion_port) return NVRM_SS_OFF;
    struct NVRMSurfShareEsc request = {0};
    request.version = NVRM_SURFSHARE_VERSION; request.surfaceID = sid;
    request.plane = NVRM_SS_PLANE_GPU_MARK | (pending ? 1u : 0u);
    request.status = NVRM_SS_OFF;
    uint64_t command = NVRM_ESC_SURF_DIRTY; size_t size = sizeof request;
    atomic_fetch_add(&g6mf_completion_calls, 1);
    kern_return_t kr = IOConnectCallMethod(g6mf_completion_port, 1, &command, 1,
        &request, sizeof request, NULL, NULL, &request, &size);
    if (kr != KERN_SUCCESS || size != sizeof request) {
        atomic_fetch_add(&g6mf_completion_errors, 1); return NVRM_SS_OFF;
    }
    return request.status;
}
void g6mf_completion_channel_stats(uint64_t out[3]) {
    out[0] = g6mf_completion_port != 0;
    out[1] = atomic_load(&g6mf_completion_calls);
    out[2] = atomic_load(&g6mf_completion_errors);
}

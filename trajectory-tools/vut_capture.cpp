#include "vut/vut_client.h"
#include "vut/vut_types.h"

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <deque>
#include <fstream>
#include <iostream>
#include <map>
#include <mutex>
#include <string>
#include <thread>

namespace {

struct Sample {
    vut::Pose pose;
    uint32_t state;
};

std::atomic<bool> g_stop(false);

void on_signal(int)
{
    g_stop.store(true);
}

bool parse_seconds(const char* value, unsigned int* seconds)
{
    char* end = nullptr;
    const unsigned long parsed = std::strtoul(value, &end, 10);
    if (*value == '\0' || *end != '\0' || parsed == 0 || parsed > 86400)
        return false;
    *seconds = static_cast<unsigned int>(parsed);
    return true;
}

} // namespace

int main(int argc, char** argv)
{
    if (argc < 2 || argc > 3) {
        std::cerr << "Usage: " << argv[0] << " OUTPUT.csv [SECONDS]\n";
        return 2;
    }

    unsigned int seconds = 60;
    if (argc == 3 && !parse_seconds(argv[2], &seconds)) {
        std::cerr << "SECONDS must be an integer from 1 to 86400.\n";
        return 2;
    }

    std::ofstream csv(argv[1]);
    if (!csv) {
        std::perror(argv[1]);
        return 1;
    }
    csv << "timestamp_ns,device_id,serial,state,x_m,y_m,z_m,qx,qy,qz,qw,"
           "vx_mps,vy_mps,vz_mps,wx_radps,wy_radps,wz_radps,flags\n";

    std::mutex mutex;
    std::condition_variable sample_ready;
    std::deque<Sample> samples;
    std::map<uint32_t, uint32_t> states;
    std::atomic<unsigned long long> written(0);
    bool producer_done = false;

    std::thread writer([&] {
        for (;;) {
            Sample sample{};
            {
                std::unique_lock<std::mutex> lock(mutex);
                sample_ready.wait(lock, [&] { return producer_done || !samples.empty(); });
                if (samples.empty() && producer_done)
                    break;
                sample = samples.front();
                samples.pop_front();
            }

            const vut::Pose& p = sample.pose;
            csv << p.timestamp_ns << ',' << p.device_id << ',' << p.serial << ','
                << sample.state << ',' << p.position[0] << ',' << p.position[1] << ','
                << p.position[2] << ',' << p.orientation[0] << ',' << p.orientation[1]
                << ',' << p.orientation[2] << ',' << p.orientation[3] << ','
                << p.velocity[0] << ',' << p.velocity[1] << ',' << p.velocity[2] << ','
                << p.angular_velocity[0] << ',' << p.angular_velocity[1] << ','
                << p.angular_velocity[2] << ',' << p.flags << '\n';
            ++written;
        }
        csv.flush();
    });

    vut::Client client("/tmp/vut.sock");
    client.set_auto_reconnect(true, 200, 2000);
    client.on_status([&](const vut::Status& status) {
        std::lock_guard<std::mutex> lock(mutex);
        states[status.device_id] = status.state;
    });
    client.on_pose([&](const vut::Pose& pose) {
        std::lock_guard<std::mutex> lock(mutex);
        const std::map<uint32_t, uint32_t>::const_iterator it = states.find(pose.device_id);
        if (it != states.end() && it->second == vut::DEV_READY) {
            samples.push_back(Sample{pose, it->second});
            sample_ready.notify_one();
        }
    });

    std::signal(SIGINT, on_signal);
    std::signal(SIGTERM, on_signal);

    if (client.connect("vut_capture", vut::SUB_ALL) != 0)
        std::cerr << "Waiting for VIVE Hub tracker_server at /tmp/vut.sock...\n";

    std::cout << "Recording ready-state poses for " << seconds << " seconds. Press Ctrl-C to stop.\n";
    const std::chrono::steady_clock::time_point deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(seconds);
    while (!g_stop.load() && std::chrono::steady_clock::now() < deadline)
        std::this_thread::sleep_for(std::chrono::milliseconds(100));

    client.disconnect();
    {
        std::lock_guard<std::mutex> lock(mutex);
        producer_done = true;
    }
    sample_ready.notify_one();
    writer.join();

    std::cout << "Wrote " << written.load() << " pose samples to " << argv[1] << "\n";
    return written.load() == 0 ? 3 : 0;
}

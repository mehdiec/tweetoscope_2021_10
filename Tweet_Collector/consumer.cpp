

#include "tweetoscopeCollectorParams.hpp"
#include "tweet.hpp"
int main(int argc, char *argv[])
{

    auto msg = consumer.poll();
    if (msg && !msg.get_error())
    {
        tweetoscope::tweet twt;
        auto key = tweetoscope::cascade::idf(std::stoi(msg.get_key()));
        auto istr = std::istringstream(std::string(msg.get_payload()));
        istr >> twt;
    }
    return 0;
}
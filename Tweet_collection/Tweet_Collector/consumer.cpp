#include <cppkafka/cppkafka.h>

#include "tweetoscopeCollectorParams.hpp"
#include "tweet.hpp"

using namespace cppkafka;
int main(int argc, char *argv[])
{
    if (argc != 2)
    {
        std::cout << "Usage : " << argv[0] << " <config-filename>" << std::endl;
        return 0;
    }
    tweetoscope::params::collector params(argv[1]);

    Configuration config = {
        {"metadata.broker.list", params.kafka.brokers},

    };
    Consumer consumer(config);
    consumer.subscribe({params.topic.in});
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

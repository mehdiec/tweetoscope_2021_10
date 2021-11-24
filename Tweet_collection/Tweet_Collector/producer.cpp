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
        {"metadata.broker.list", params.kafka.brokers}};

    // Create the producer
    Producer producer(config);
    //auto int_key = MessageBuilder(params.topic.in).partition(0);
    //auto key = std::to_string(int_key);
    //MessageBuilder builder = MessageBuilder(params.topic.in).partition(0);
    //builder.key(key);
    std::string msg = "hey there!";
    std::ostringstream ostr;
    ostr << msg; //... the JSON message auto msg = ostr.str();

    producer.produce(MessageBuilder(params.topic.in).partition(0).payload(msg));

    return 0;
}

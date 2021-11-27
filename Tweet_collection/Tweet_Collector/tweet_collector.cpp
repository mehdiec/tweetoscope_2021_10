#include "tweetoscopeCollectorParams.hpp"
#include <cppkafka/cppkafka.h>
#include "tweet.hpp"
#include <boost/heap/binomial_heap.hpp>
#include <map>
#include <queue>
int main(int argc, char *argv[])
{

    if (argc != 2)
    {
        std::cout << "Usage : " << argv[0] << " <config-filename>" << std::endl;
        return 0;
    }
    tweetoscope::params::collector params(argv[1]);
    std::cout << std::endl
              << "Parameters : " << std::endl
              << "----------" << std::endl
              << std::endl
              << params << std::endl
              << std::endl;

    cppkafka::Configuration cons_config = {
        {"metadata.broker.list", params.kafka.brokers},

    };
    cppkafka::Consumer consumer(cons_config);
    consumer.subscribe({params.topic.in});
    cppkafka::Configuration prod_config = {
        {"metadata.broker.list", params.kafka.brokers}};

    // Create the producer
    cppkafka::Producer producer(prod_config);

    cppkafka::MessageBuilder PartialMessageBuilder{params.topic.out_series};

    // Implementation of a Producer which write on terminated Cascades : properties
    cppkafka::MessageBuilder TerminatedMessageBuilder{params.topic.out_properties};
    tweetoscope::params::section::Times time;
    time.observation = params.times.observation;
    time.terminated = params.times.terminated;

    auto msg = consumer.poll();
    std::map<tweetoscope::source::idf, tweetoscope::cascade::Processor> map_idf_processor;

    using cascade_ref = std::shared_ptr<tweetoscope::cascade::Cascade>;
    using cascade_wck = std::weak_ptr<tweetoscope::cascade::Cascade>;
    std::map<tweetoscope::timestamp, std::queue<cascade_wck>> partial_cascade_map;
    // Assert msg is not empty and there no errors
    if (msg && !msg.get_error())
    {
        // Instanciation of a tweet
        tweetoscope::tweet twt;
        auto init_key = tweetoscope::cascade::idf(std::stoi(msg.get_key()));
        auto istr = std::istringstream(std::string(msg.get_payload()));
        istr >> twt;

        //  Creating processor of the source if not already created
        auto key = std::to_string(init_key);

        tweetoscope::cascade::Processor processor_new(twt);
        if (map_idf_processor.find(twt.source) == map_idf_processor.end())
        {
            tweetoscope::cascade::Processor processor(twt);
            map_idf_processor[twt.source] = processor_new;
        }

        tweetoscope::cascade::Processor *processor = &map_idf_processor.at(twt.source);
        if (twt.type == "tweet")
        {
            processor->source_time = twt.time;
            tweetoscope::cascade::cascade_ref ref_cascade = tweetoscope::cascade::Cascade::make_cascade_ref(twt, key);

            auto location = processor->update_queue(ref_cascade);
        }
        else
        {
        }

        return 0;
    }
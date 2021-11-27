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
    std::map<std::string, tweetoscope::cascade::priority_queue::handle_type> map_key_location;
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

            map_idf_processor.insert(std::make_pair(twt.source, processor_new));
        }

        tweetoscope::cascade::Processor *processor = &map_idf_processor.at(twt.source);
        if (twt.type == "tweet")
        {
            processor->source_time = twt.time;
            cascade_ref ref_cascade = tweetoscope::cascade::Cascade::make_cascade_ref(twt, key);
            cascade_wck wck_cascade = ref_cascade;

            auto location = processor->update_queue(ref_cascade);
            map_key_location.insert(std::make_pair(key, location));

            for (auto &observation : time.observation)
            {
                processor->fifo[observation].push(wck_cascade);
            }

            processor->symbol_table.insert(std::make_pair(key, wck_cascade));
        }
        else
        {
            cascade_wck wck_cascade = processor->symbol_table.at(key);
            if (auto ref_cascade = wck_cascade.lock(); ref_cascade)
            {
                ref_cascade->cascade_update(twt, key);
                processor->source_time = twt.time;
                processor->cascade_queue.decrease(map_key_location[key], ref_cascade);
            }
        }
        // series
        std::vector<std::string> series = processor->send_partial_cascade(time.observation);
        for (auto &serie : series)
        {
            std::cout << "Sending Partial Cascades : " << serie << std::endl;
            PartialMessageBuilder.payload(serie);

            producer.produce(PartialMessageBuilder);
        }

        // properties
        std::vector<std::string> propertiesToSend = processor->send_terminated_cascade(time.terminated, params.cascade.min_cascade_size);
        for (auto &msg_properties : propertiesToSend)
        {
            std::cout << "Sending Terminated Cascades : " << msg_properties << std::endl;
            TerminatedMessageBuilder.payload(msg_properties);
            int i = 0;
            for (auto T_obs : time.observation)
            {
                auto T_obs_key = std::to_string(T_obs);
                TerminatedMessageBuilder.partition(i);
                i++;
                TerminatedMessageBuilder.key(T_obs_key);

                producer.produce(TerminatedMessageBuilder);
            }
        }
    }
    return 0;
}
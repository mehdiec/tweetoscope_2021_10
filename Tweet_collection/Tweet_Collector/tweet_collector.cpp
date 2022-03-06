#include "tweetoscopeCollectorParams.hpp"
#include <cppkafka/cppkafka.h>
#include "tweet.hpp"
#include "tweetProcessing.cpp"
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
        {"auto.offset.reset", "earliest"},
        {"group.id", "testconsumers"},

    };
    cppkafka::Consumer consumer(cons_config);
    consumer.subscribe({params.topic.in});
    std::cout << "Consumer DONE" << std::endl;
    std::cout << "-------------------------------" << std::endl
              << std::endl;

    cppkafka::Configuration prod_config = {
        {"metadata.broker.list", params.kafka.brokers}};

    // Create the producer
    cppkafka::Producer producer(prod_config);

    cppkafka::MessageBuilder PartialMessageBuilder{params.topic.out_series};

    cppkafka::MessageBuilder TerminatedMessageBuilder{params.topic.out_properties};
    std::cout << "Producer Done" << std::endl;
    std::cout << "-------------------------------" << std::endl
              << std::endl;

    tweetoscope::params::section::Times time;
    time.observation = params.times.observation;
    time.terminated = params.times.terminated;
    std::cout << "observation" << std::endl;
    std::cout << time.terminated << std::endl
              << std::endl;

    std::map<tweetoscope::source::idf, tweetoscope::cascade::Processor> map_idf_processor;
    std::map<std::string, tweetoscope::cascade::priority_queue::handle_type> map_key_location;
    using cascade_ref = std::shared_ptr<tweetoscope::cascade::Cascade>;
    using cascade_wck = std::weak_ptr<tweetoscope::cascade::Cascade>;
    std::map<tweetoscope::timestamp, std::queue<cascade_wck>> partial_cascade_map;
    bool keep = true;
    std::cout << "Loop" << std::endl;
    std::cout << "-------------------------------" << std::endl
              << std::endl;

    while (keep)
    {
        auto msg = consumer.poll();
        // check if the msg is not empty and there no errors
        if (msg && !msg.get_error())
        {
            // Instanciation of a tweet
            tweetoscope::tweet twt;
            auto init_key = tweetoscope::cascade::idf(std::stoi(msg.get_key()));
            auto istr = std::istringstream(std::string(msg.get_payload()));
            istr >> twt;

            //  Creating processor of the source if not already created
            auto key = std::to_string(init_key);
            // assert if their is no processor for this tweet
            if (map_idf_processor.find(twt.source) == map_idf_processor.end())
            {
                tweetoscope::cascade::Processor processor(twt);
                map_idf_processor.insert(std::make_pair(twt.source, processor));
            }
            // get the share pointer coresponding to the tweet or the retweet source
            tweetoscope::cascade::Processor *processor = &map_idf_processor.at(twt.source);
            if (twt.type == "tweet")
            {

                // updating the source time of the processor
                processor->update_newest_source_time(twt);
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
                cascade_wck wck_cascade = processor->symbol_table[key];

                if (auto ref_cascade = wck_cascade.lock(); ref_cascade)
                {

                    ref_cascade->cascade_update(twt, key);
                    processor->update_newest_source_time(twt);
                    if (map_key_location[key].node_ != 0)
                    {
                        // processor->decrease_priority(map_key_location[key], ref_cascade);
                    }
                    else
                    {
                        processor->symbol_table.erase(key);
                        map_key_location.erase(key);
                    }
                }
            }
            // series

            std::vector<std::string> series = processor->send_partial_cascade(time.observation);
            std::vector<std::string> propertiesToSend = processor->send_terminated_cascade(time.terminated, params.cascade.min_cascade_size);
            if (series.size() != 0)
            {
                for (auto &serie : series)
                {
                    std::cout << "Sending Partial Cascades : " << serie << std::endl;
                    PartialMessageBuilder.payload(serie);
                    // sending the message
                    producer.produce(PartialMessageBuilder);
                }
            }

            //// properties

            if (propertiesToSend.size() != 0)
            {

                for (auto &msg_properties : propertiesToSend)
                {
                    std::cout << "Sending Terminated Cascades : " << msg_properties << std::endl;
                    TerminatedMessageBuilder.payload(msg_properties);
                    for (auto T_obs : time.observation)
                    {
                        auto T_obs_key = std::to_string(T_obs);
                        TerminatedMessageBuilder.key(T_obs_key);

                        try
                        {
                            // Try to send message
                            producer.produce(TerminatedMessageBuilder);
                        }
                        catch (const cppkafka::HandleException &e)
                        {
                            std::ostringstream ostr;
                            ostr << e.what();
                            std::string error{ostr.str()};
                            if (error.compare("Queue full") != 0)
                            {
                                std::chrono::milliseconds timeout(1200);
                                producer.flush(timeout);
                                producer.produce(TerminatedMessageBuilder);
                            }
                            else
                            {
                                std::cout << "Something went wrong: " << e.what() << std::endl;
                            }
                        }
                    }
                }
            }
        }
    }
    return 0;
}


#pragma once

#include <tuple>
#include <string>
#include <iostream>
#include <fstream>
#include <vector>
#include <cstddef>
#include <stdexcept>
#include <boost/heap/binomial_heap.hpp>
namespace tweetoscope
{

    using timestamp = std::size_t;
    namespace source
    {
        using idf = std::size_t;
    }
    struct tweet
    {
        std::string type = "";
        std::string msg = "";
        timestamp time = 0;
        double magnitude = 0;
        source::idf source = 0;
        std::string info = "";
    };
    namespace cascade
    {
        struct Cascade;

        using idf = std::size_t;
        using cascade_ref = std::shared_ptr<Cascade>;
        using cascade_wck = std::weak_ptr<Cascade>;

        struct cascade_ref_comparator
        {
            bool operator()(cascade_ref cascade1, cascade_ref cascade2) const; // Defined later.
        };

        using priority_queue = boost::heap::binomial_heap<cascade_ref,
                                                          boost::heap::compare<cascade_ref_comparator>>;

        std::ostream &operator<<(std::ostream &os, std::vector<std::pair<timestamp, double>> &vect)
        {
            os << '[';
            auto it = vect.begin();
            if (it != vect.end())
            {
                os << " [" << (it)->first << ',' << (it++)->second << "] ";
                while (it != vect.end())
                    os << ", "
                       << " [" << (it++)->first << ',' << (it++)->second << "] ";
            }

            os << "]";
            return os;
        };

        struct Cascade
        {
            //(or any other name) for storing cascade information (i.e. the identifier, the message of the first tweet, the collection of retweet magnitudes and time, etc…).
            //Define a type like using to handle cascade instances.

            std::string cid;
            std::string msg = "";
            timestamp time_first_twt;
            timestamp time_last_twt;
            double magnitude;
            source::idf source;
            std::vector<std::pair<timestamp, double>> tweets;
            Cascade(tweet &twt, std::string &key) : cid(key),
                                                    msg(twt.msg),
                                                    time_first_twt(twt.time),
                                                    time_last_twt(twt.time),
                                                    tweets({std::make_pair(twt.time, twt.magnitude)}),
                                                    source(twt.source){};
            ~Cascade(){};
            static cascade_ref make_cascade_ref(tweet &twt, std::string &key) { return std::make_shared<Cascade>(twt, key); }
            void cascade_update(tweet &twt, std::string &key)
            {
                tweets.push_back(std::make_pair(twt.time, twt.magnitude));
                time_last_twt = twt.time;
            };
            bool operator<(const Cascade &cascade) const { return time_last_twt < cascade.time_last_twt; }
        };

        bool cascade_ref_comparator::operator()(cascade_ref cascade1, cascade_ref cascade2) const
        {
            return *cascade1 < *cascade2;
        };
        struct Processor
        {

            source::idf source;
            timestamp source_time;
            priority_queue cascade_queue;
            std::map<timestamp, std::queue<cascade_wck>> fifo;
            std::map<std::string, cascade_wck> symbol_table;
            Processor(const Processor &) = default;
            Processor &operator=(const Processor &) = default;

            ~Processor(){};

            Processor(tweet &twt) : source(twt.source), source_time(twt.time), cascade_queue{}, fifo{}, symbol_table{} {};
            auto update_queue(cascade_ref ref_cascade)
            {
                return cascade_queue.push(ref_cascade);
            }
            std::vector<std::string> send_partial_cascade(std::vector<timestamp> observations)
            {

                std::vector<std::string> data;
                for (auto observation : observations)
                {

                    if (!fifo[observation].empty())
                    {
                        cascade_wck wck_cascade = fifo[observation].front();
                        auto ref_cascade = wck_cascade.lock();

                        while (source_time - (ref_cascade->time_first_twt) > observation) //while the duration from the first event until the current timestamp is greater than the observation window
                        {
                            // creating the partial cascade
                            std::vector<std::pair<timestamp, double>> partial_tweets;
                            for (auto it = ref_cascade->tweets.begin(); (it->first - ref_cascade->time_first_twt <= observation) && (it != ref_cascade->tweets.end()); ++it)
                            {
                                partial_tweets.push_back(*it);
                            }

                            std::ostringstream ostr;

                            //cascade_series  { 'type' : 'serie', 'cid': 'tw23981', 'msg' : 'blah blah', 'T_obs': 600, 'tweets': [ (102, 1000), (150,12), ... ] }
                            ostr << "{"
                                 << "\"type\": "
                                 << "serie"
                                 << "\"cid\":" << ref_cascade->cid
                                 << "\"msg\":" << ref_cascade->msg
                                 << "\"T_obs\":" << observation
                                 << "\"tweets\":" << partial_tweets
                                 << '}';
                            data.push_back(ostr.str());
                            fifo[observation].pop();
                            if (!fifo[observation].empty())
                            {
                                wck_cascade = fifo[observation].front();
                                auto ref_cascade = wck_cascade.lock();
                            }
                            else
                            {
                                break;
                            }
                        }
                    }
                }
                return data;
            }

            std::vector<std::string> send_terminated_cascade(timestamp &t_terminated, std::size_t min_cascade_size)
            {
                std::vector<std::string> data;

                while (!cascade_queue.empty())
                {
                    auto ref_cascade = cascade_queue.top();

                    if ((source_time - ref_cascade->time_last_twt) > t_terminated && ref_cascade->tweets.size() > min_cascade_size)
                    {
                        std::ostringstream ostr;

                        cascade_queue.pop();
                        //cascade_properties { 'type' : 'size', 'cid': 'tw23981', 'n_tot': 127, 't_end': 4329 }

                        ostr << "{"
                             << "\"type\": "
                             << "size"
                             << "\"cid\":" << ref_cascade->cid
                             << "\"n_tot\":" << ref_cascade->tweets.size()
                             << "\"t_end\":" << ref_cascade->time_last_twt
                             << '}';

                        data.push_back(ostr.str());
                    }
                };
                return data;
            };
        };

    }

    inline std::string get_string_val(std::istream &is)
    {
        char c;
        is >> c; // eats  "
        std::string value;
        std::getline(is, value, '"'); // eats tweet", but value has tweet
        return value;
    }

    inline std::istream &operator>>(std::istream &is, tweet &t)
    {
        // A tweet is  : {"type" : "tweet"|"retweet",
        //                "msg": "...",
        //                "time": timestamp,
        //                "magnitude": 1085.0,
        //                "source": 0,
        //                "info": "blabla"}
        std::string buf;
        char c;
        is >> c; // eats '{'
        is >> c; // eats '"'
        while (c != '}')
        {
            std::string tag;
            std::getline(is, tag, '"'); // Eats until next ", that is eaten but not stored into tag.
            is >> c;                    // eats ":"
            if (tag == "type")
                t.type = get_string_val(is);
            else if (tag == "msg")
                t.msg = get_string_val(is);
            else if (tag == "info")
                t.info = get_string_val(is);
            else if (tag == "t")
                is >> t.time;
            else if (tag == "m")
                is >> t.magnitude;
            else if (tag == "source")
                is >> t.source;

            is >> c; // eats either } or ,
            if (c == ',')
                is >> c; // eats '"'
        }
        return is;
    }
}

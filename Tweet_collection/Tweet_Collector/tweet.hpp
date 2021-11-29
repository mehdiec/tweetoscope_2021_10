
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

            is >> c; // eats ":"
            if (tag == "type")
            {

                t.type = get_string_val(is);
            }

            else if (tag == "msg")
            {
                t.msg = get_string_val(is);
            }
            else if (tag == "fo")
            {
                t.info = get_string_val(is);
            }
            else if (tag == "t")
            {
                is >> t.time;
            }
            else if (tag == "m")
            {
                is >> t.magnitude;
            }

            else if (tag == "tweet_id")
            {
                is >> t.source;
            }
            is >> c; // eats either } or ,
            if (c == ',')
                is >> c; // eats '"'
        }
        return is;
    }

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

            for (auto it = vect.begin(); (it != (vect.end() - 1)); ++it)
            {
                os << " [" << (it)->first << ',' << (it)->second << "] ,";
            }
            auto it = (vect.end() - 1);

            os << " [" << (it)->first << ',' << (it)->second << "] ";

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
            source::idf source;
            std::vector<std::pair<timestamp, double>> tweets;

            Cascade(tweet &twt, std::string &key) : cid(key),
                                                    msg(twt.msg),
                                                    time_first_twt(twt.time),
                                                    time_last_twt(twt.time),
                                                    source(twt.source),
                                                    tweets({std::make_pair(twt.time, twt.magnitude)}){};
            ~Cascade(){};
            static cascade_ref make_cascade_ref(tweet &twt, std::string &key) { return std::make_shared<Cascade>(twt, key); }

            void cascade_update(tweet &twt, std::string &key)
            {
                tweets.push_back(std::make_pair(twt.time, twt.magnitude));
                time_last_twt = twt.time;
            };

            bool operator<(const Cascade &cascade) const { return time_last_twt < cascade.time_last_twt; }

            std::ostringstream make_size(timestamp source_time)
            {
                std::ostringstream ostr;
                ostr << "{"
                     << "\"type\": "
                     << "size, "
                     << "\"cid\":" << cid
                     << ", \"n_tot\":" << tweets.size()
                     << ", \"t_end\":" << (time_last_twt)
                     << '}';

                return ostr;
            }

            std::ostringstream make_serie(timestamp source_time, timestamp observation)
            {
                std::ostringstream ostr;
                std::vector<std::pair<timestamp, double>> partial_tweets;
                for (auto it = tweets.begin(); (it->first - time_first_twt <= observation) && (it != tweets.end()); ++it)
                {
                    auto time = it->first - time_first_twt;

                    partial_tweets.push_back(std::make_pair(time, it->second));
                }
                ostr << "{"
                     << "\"type\": "
                     << "serie, "
                     << "\"cid\":" << cid
                     << ", \"msg\":" << msg
                     << ", \"T_obs\":" << observation
                     << ", \"tweets\":" << partial_tweets
                     << '}';

                return ostr;
            }
        };

        bool cascade_ref_comparator::operator()(cascade_ref cascade1, cascade_ref cascade2) const
        {
            return *cascade1 < *cascade2;
        };
        struct Processor
        {

            source::idf source;
            timestamp source_time;
            timestamp newest_source_time;
            priority_queue cascade_queue;
            std::map<timestamp, std::queue<cascade_wck>> fifo;
            std::map<std::string, cascade_wck> symbol_table;
            Processor(const Processor &) = default;
            Processor &operator=(const Processor &) = default;

            ~Processor(){};

            Processor(tweet &twt) : source(twt.source), source_time(twt.time), newest_source_time(twt.time), cascade_queue{}, fifo{}, symbol_table{} {};
            void update_newest_source_time(tweet &twt)
            {
                newest_source_time = twt.time;
            }

            void decrease_priority(auto location, cascade_ref ref_cascade)
            {
                return cascade_queue.decrease(location, ref_cascade);
            }
            auto update_queue(cascade_ref ref_cascade)
            {
                return cascade_queue.push(ref_cascade);
            }

            bool terminated(timestamp &t_terminated, cascade_ref ref_cascade, bool observation = false)
            {

                if (observation)
                    return ((newest_source_time - source_time) > t_terminated);
                else
                {
                    if ((newest_source_time - source_time) > t_terminated)
                    {
                        return true;
                    }
                    else
                    {
                        source_time = newest_source_time;
                        return false;
                    }
                }
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

                        while (terminated(observation, ref_cascade, true)) //while the duration from the first event until the current timestamp is greater than the observation window
                        {
                            // creating the partial cascade

                            std::ostringstream ostr = ref_cascade->make_serie(source_time, observation);
                            data.push_back(ostr.str());
                            fifo[observation].pop();

                            if (!fifo[observation].empty())
                            {

                                cascade_wck wck_cascade = fifo[observation].front();
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

                if (!cascade_queue.empty())
                {
                    auto ref_cascade = cascade_queue.top();

                    //cascade_properties { 'type' : 'size', 'cid': 'tw23981', 'n_tot': 127, 't_end': 4329 }

                    while (terminated(t_terminated, ref_cascade))
                    {
                        if (ref_cascade->tweets.size() > min_cascade_size)
                        {
                            std::ostringstream ostr = ref_cascade->make_size(source_time);

                            std::ostringstream os = ref_cascade->make_size(source_time);

                            //cascade_properties { 'type' : 'size', 'cid': 'tw23981', 'n_tot': 127, 't_end': 4329 }

                            data.push_back(ostr.str());
                            os << std::endl;
                        }

                        cascade_queue.pop();
                        if (!cascade_queue.empty())
                        {

                            ref_cascade = cascade_queue.top();
                        }
                        else
                        {
                            return data;
                        }
                    };
                }
                return data;
            };
        };

    }

}

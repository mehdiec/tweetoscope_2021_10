#pragma once

#include <tuple>
#include <string>
#include <iostream>
#include <fstream>
#include <vector>
#include <cstddef>
#include <stdexcept>
#include <map>
#include <boost/heap/binomial_heap.hpp>
#include "tweet.hpp"

namespace tweetoscope
{
    namespace cascade
    {
        struct Cascade;

        using idf = std::size_t;
        using cascade_ref = std::shared_ptr<Cascade>;
        using cascade_wck = std::weak_ptr<Cascade>;

        struct cascade_ref_comparator
        {
            bool operator()(cascade_ref cascade1, cascade_ref cascade2) const;
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

            /**
             * Method creating finished cascades for each observation windows.
             *
             * 
             * @return cascade_properties { 'type' : 'size', 'cid': 'tw23981', 'n_tot': 127, 't_end': 4329 }
             */
            std::ostringstream make_size()
            {
                std::ostringstream ostr;
                ostr << "{"
                     << "\"type\": "
                     << "\"size\", "
                     << "\"cid\":" << cid
                     << ", \"n_tot\":" << tweets.size()
                     << ", \"t_end\":" << (time_last_twt)
                     << '}';

                return ostr;
            }

            /**
             * Method creating partial cascades for each observation windows.
             *
             * @param source_time timestamp of the source ie. processor source time @param observation observation window consideres .
             * @return cascade_series { 'type' : 'serie', 'cid': 'tw23981', 'msg' : 'blah blah', 'T_obs': 600, 'tweets': [ (102, 1000), (150,12), ... ] }
             */
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
                     << "\"serie\", "
                     << "\"cid\":" << cid
                     << ", \"msg\":  \"msg\""

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
            timestamp first_tweet;
            timestamp source_time;
            timestamp newest_source_time;
            priority_queue cascade_queue;
            std::map<timestamp, std::queue<cascade_wck>> fifo;
            std::map<std::string, cascade_wck> symbol_table;
            Processor(const Processor &) = default;
            Processor &operator=(const Processor &) = default;

            ~Processor(){};

            /**
             * Instanciate a processor.
             *
             * @param twt a tweet.
             * 
             */
            Processor(tweet &twt) : source(twt.source), first_tweet(twt.time), source_time(twt.time), newest_source_time(twt.time), cascade_queue{}, fifo{}, symbol_table{} {};

            /**
             * updates the source time of a processor.
             *
             * @param twt a tweet.
             * @return 
             */
            void update_newest_source_time(tweet &twt)
            {
                newest_source_time = twt.time;
            }

            void decrease_priority(auto location, cascade_ref ref_cascade)
            {
                return cascade_queue.decrease(location, ref_cascade);
            }

            /**
             * updates the priority queue with the most recent cascade.
             *
             * @param ref_cascade shared pointer to the considered cascade.
             * @return updated queue
             */
            auto update_queue(cascade_ref ref_cascade)
            {
                return cascade_queue.push(ref_cascade);
            }

            /**
             * Check if a cascade could be consider terminated according to the time and updating source time.
             *
             * @param t_terminated time between two tweet/retweet to consider  a cascade as terminated  @param ref_cascade shared pointer to the considered cascade  @param observation whether or not we using observation windows or not.
             * @return bool
             */
            bool terminated(timestamp &t_terminated, cascade_ref ref_cascade, bool observation = false)
            {
                if (observation)
                    return ((source_time - first_tweet) > t_terminated);
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
            /**
             * Creating partial cascades for each observation windows.
             *
             * @param observations vector of timestamps representing observation windows.
             * @return vector of cascade_series { 'type' : 'serie', 'cid': 'tw23981', 'msg' : 'blah blah', 'T_obs': 600, 'tweets': [ (102, 1000), (150,12), ... ] }
             */
            std::vector<std::string> send_partial_cascade(std::vector<timestamp> observations)
            {
                std::vector<std::string> data;
                for (auto observation : observations)
                {
                    if (!fifo[observation].empty())
                    {
                        cascade_wck wck_cascade = fifo[observation].front();
                        auto ref_cascade = wck_cascade.lock();
                        while (terminated(observation, ref_cascade, true)) //while the duration from the first event until the current timestamp is greater than the observation window we create partial cascade
                        {
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
            /**
             * Creating finished cascades.
             *
             * @param min_cascade_size size to consider a cascade as terminated @param t_terminated time between two tweet/retweet to consider  a cascade as terminated .
             * @return vector of cascade_properties { 'type' : 'size', 'cid': 'tw23981', 'n_tot': 127, 't_end': 4329 }
             */
            std::vector<std::string> send_terminated_cascade(timestamp &t_terminated, std::size_t min_cascade_size)
            {
                std::vector<std::string> data;
                if (!cascade_queue.empty())
                {
                    auto ref_cascade = cascade_queue.top();
                    while (terminated(t_terminated, ref_cascade))
                    {
                        if (ref_cascade->tweets.size() > min_cascade_size)
                        {
                            std::ostringstream ostr = ref_cascade->make_size();
                            //cascade_properties { 'type' : 'size', 'cid': 'tw23981', 'n_tot': 127, 't_end': 4329 }
                            data.push_back(ostr.str());
                            ref_cascade.reset();
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
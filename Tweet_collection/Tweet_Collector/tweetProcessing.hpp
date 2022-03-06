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
        /**
         * @brief Cascade class
         *
         */
        struct Cascade;

        using idf = std::size_t;
        using cascade_ref = std::shared_ptr<Cascade>;
        using cascade_wck = std::weak_ptr<Cascade>;

        struct cascade_ref_comparator
        { /**
           * @brief Overload () operator
           *
           * @param ref_c1
           * @param ref_c2
           * @return true
           * @return false
           */
            bool operator()(cascade_ref cascade1, cascade_ref cascade2) const;
        };
        // overloading of << operator
        /**
         * @brief Overload operator << to add time and magnitude to an output to print
         *
         * @param os
         * @param time_magnitude
         * @return std::ostream&
         */
        std::ostream &operator<<(std::ostream &os, std::vector<std::pair<timestamp, double>> &vect);

        // Implementation of the Cascade class
        struct Cascade
        {
            //(or any other name) for storing cascade information (i.e. the identifier, the message of the first tweet, the collection of retweet magnitudes and time, etc…).
            // Define a type like using to handle cascade instances.

            std::string cid;
            std::string msg = "";
            timestamp time_first_twt;
            timestamp time_last_twt;
            source::idf source;
            std::vector<std::pair<timestamp, double>> tweets;

            // Constructors

            /**
             * @brief Construct a new Cascade object from a tweet (std::string) and a key (std::string)
             *
             * @param twt
             * @param key
             */
            Cascade(tweet &twt, std::string &key);

            // Destructor

            /**
             * @brief Destroy the Cascade object
             *
             */
            ~Cascade(){};

            /**
             * @brief Create a share pointer of cascade
             *
             * @param twt
             * @param key
             */
            static cascade_ref make_cascade_ref(tweet &twt, std::string &key) { return std::make_shared<Cascade>(twt, key); }

            // Others
            /**
             * @brief Add a tweet to a cascade object
             *
             * @param twt
             * @param key
             */
            void cascade_update(tweet &twt, std::string &key);
            /**
             * @brief Overload operator < to compare the cascade object from its sharepointer reference with another reference of a cascade
             *
             * @param ref_other_cascade
             * @return true
             * @return false
             */
            bool operator<(const Cascade &cascade) const;

            /**
             * Method creating finished cascades for each observation windows.
             *
             *
             * @return cascade_properties { 'type' : 'size', 'cid': 'tw23981', 'n_tot': 127, 't_end': 4329 }
             */
            std::ostringstream make_size();

            /**
             * Method creating partial cascades for each observation windows.
             *
             * @param source_time timestamp of the source ie. processor source time @param observation observation window consideres .
             * @return cascade_series { 'type' : 'serie', 'cid': 'tw23981', 'msg' : 'blah blah', 'T_obs': 600, 'tweets': [ (102, 1000), (150,12), ... ] }
             */
            std::ostringstream make_serie(timestamp source_time, timestamp observation);
        };

        using priority_queue = boost::heap::binomial_heap<cascade_ref,
                                                          boost::heap::compare<cascade_ref_comparator>>;
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
            /**
             * @brief Destroy the Processor object
             *
             */
            ~Processor(){};

            /**
             * Instanciate a processor.
             *
             * @param twt a tweet.
             *
             */
            Processor(tweet &twt);

            /**
             * updates the source time of a processor.
             *
             * @param twt a tweet.
             * @return
             */
            void update_newest_source_time(tweet &twt);
            /**
             * @brief Remove a Cascade of the Priority Queue from the share pointer that references the cascade object
             *
             * @param elt
             * @param sh_ref_cascade
             */
            void decrease_priority(priority_queue::handle_type location, cascade_ref ref_cascade);

            /**
             * updates the priority queue with the most recent cascade.
             *
             * @param ref_cascade shared pointer to the considered cascade.
             * @return updated queue
             */
            auto update_queue(cascade_ref ref_cascade);

            /**
             * Check if a cascade could be consider terminated according to the time and updating source time.
             *
             * @param t_terminated time between two tweet/retweet to consider  a cascade as terminated  @param ref_cascade shared pointer to the considered cascade  @param observation whether or not we using observation windows or not.
             * @return bool
             */
            bool terminated(timestamp &t_terminated, cascade_ref ref_cascade, bool observation = false);
            /**
             * Creating partial cascades for each observation windows.
             *
             * @param observations vector of timestamps representing observation windows.
             * @return vector of cascade_series { 'type' : 'serie', 'cid': 'tw23981', 'msg' : 'blah blah', 'T_obs': 600, 'tweets': [ (102, 1000), (150,12), ... ] }
             */
            std::vector<std::string> send_partial_cascade(std::vector<timestamp> observations);
            /**
             * Creating finished cascades.
             *
             * @param min_cascade_size size to consider a cascade as terminated @param t_terminated time between two tweet/retweet to consider  a cascade as terminated .
             * @return vector of cascade_properties { 'type' : 'size', 'cid': 'tw23981', 'n_tot': 127, 't_end': 4329 }
             */
            std::vector<std::string> send_terminated_cascade(timestamp &t_terminated, std::size_t min_cascade_size);
        };

    }
}
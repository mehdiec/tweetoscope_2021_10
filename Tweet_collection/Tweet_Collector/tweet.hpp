
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
    namespace cascade
    {
        using idf = std::size_t;
        using cascade_ref = std::shared_ptr<Cascade>;
        using priority_queue = boost::heap::binomial_heap<cascade_ref,
                                                          boost::heap::compare<cascade_ref_comparator>>;

        struct Processor
        {

            source::idf source;
            timestamp source_time;
            priority_queue cascade_queue;
            Processor(tweet &twt) : source(twt.source), source_time(twt.time), cascade_queue(){};

            ~Processor(){};

            std::vector<std::string> send_terminated_cascade(timestamp &t_terminated, std::size_t min_cascade_size)
            {

                return std::vector<std::string>();
            };
        };
        struct cascade_ref_comparator
        {
            bool operator()(cascade_ref cascade1, cascade_ref cascade2) const; // Defined later.
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
        };
        bool cascade_ref_comparator::operator()(cascade_ref cascade1, cascade_ref cascade2) const
        {
            return *cascade1 < *cascade2;
        };
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

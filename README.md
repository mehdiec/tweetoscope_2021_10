# tweetoscope_2021_10


<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/othneildrew/Best-README-Template">
    <img src="images/logo.png" alt="Logo" width="80" height="80">
  </a>



  <p align="center">

  </p>
</div>



 



<!-- ABOUT THE PROJECT -->
## About The Project

The project consists in estimating the virality of a tweet from its original message. By means of a tweet generator. We built a tweet collector in C++ that retrieves the tweet stream and sends it to the estimator under a formalism by the topic cascade_serie. An estimator using the Hawkes process simulates the tweet cascade that will be directly sent to the predictor. The predictor then estimates the virality of the tweet. Finally, a learner is implemented to continuously improve the accuracy of our model so that the prediction is better


<p align="right">(<a href="#top">back to top</a>)</p>



### Built With

This section should list any major frameworks/libraries used to bootstrap your project. Leave any add-ons/plugins for the acknowledgements section. Here are a few examples.

* [APACHE KAFKA](https://kafka.apache.org/) 
* [Docker](https://maven.apache.org/) 
* [Kubernetes](https://kubernetes.io/) 


<p align="right">(<a href="#top">back to top</a>)</p>



<!-- GETTING STARTED -->
## Getting Started

This is how you may set up the project locally.
To get a local copy up and running follow these simple steps.



<!-- ROADMAP -->
## Folder layout


    .
    ├── Build                   # Docker files (alternatively `dist`)
    ├── Deployment              # YAML files used for minikube
    ├── Pipeline_ai             # Folder containing files for the estimator, learner and predictor
    │   ├── Hawks_Processes     # files used for Hawks process
    │   └── utils               # Usefull functions
    ├── Tweet_collection        # Folder containing tweet generation and tweet collection files
    │   ├── Tweet_Collector     # tweet collection
    │   └── Tweet_Generator     # tweet generation
    ├── .gitlab-ci.yml
    └── README.md




<p align="right">(<a href="#top">back to top</a>)</p>


### Prerequisites

To run the software you need to install the following.
* docker
  ```sh
  npm install npm@latest -g
  ```

* minikube
  ```sh
  npm install npm@latest -g
  ```

### Installation

_Those are the steps to run the software._

1. Download the Deployment directory on your local machin
   ```sh
   
   ```
2. Start minikube and run the zookeeper and kafka services
   ```sh
    minikube start

    kubectl apply -f zookeeper-and-kafka.yml
   ```
3. To run the softwqre
   ```sh
   npm install
   ```

<p align="right">(<a href="#top">back to top</a>)</p>



<!-- USAGE EXAMPLES -->
## Usage



<p align="right">(<a href="#top">back to top</a>)</p>









<!-- CONTACT -->
## Authors

* **Mathieu Nalpon**
* **Mehdi Ech-Chouini**
* **Hamza Islah**



<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

Those are the libraries the project was build with.
* [gaml](https://github.com/HerveFrezza-Buet/gaml)
* [cppkafka](https://github.com/mfontanini/cppkafka)
* [kafka-python](https://kafka-python.readthedocs.io/en/master/)

<p align="right">(<a href="#top">back to top</a>)</p>




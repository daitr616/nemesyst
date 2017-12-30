#ifndef MAIN_ORS
#define MAIN_ORS

#include <iostream>
#include <mlpack/core.hpp> // please make sure path is set properly in CMakeLists.txt
//#include <armadillo>

// prototype misc functions
void helpScreen();

int main(int argc, char* argv[]) {

    int fileArgPos = 0;
    // process command line arguments
    try
    {
        // cycle through arguments
        for(int i = 0; i < argc; ++i)
        {
            std::string arg(argv[i]);
            if(i == 0)                                  {;} // do nothing
            else if(arg == "-h" || arg == "--help"  )   {helpScreen();}
            else if(arg == "-f" || arg == "--file"  )   {if(!fileArgPos){fileArgPos = i + 1;++i;std::cout << "File: " << argv[fileArgPos]<< std::endl;}}
            else                                        {std::cout << arg << " - not flag"<< std::endl;            }
        }
    }
    catch(std::exception &e)
    {

    }

    // defining data object
    arma::mat data;
    // filling data object
    //mlpack::data::Load("../DataSets/ml-20m/ratings.csv", data, true);
    if(fileArgPos)
    {
        std::string* filePath;
        mlpack::data::Load("../../../DataSets/ml-20m/pythonRatings.csv", data, true);
    }



    // test output
    std::cout << "Hello, World!" << std::endl;
    return 0;
}

void helpScreen()
{
    std::cout << "OpenRecSyst:Help"
              << std::endl;
}

#endif
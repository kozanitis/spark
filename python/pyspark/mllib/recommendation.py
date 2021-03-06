#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from pyspark import SparkContext
from pyspark.rdd import RDD
from pyspark.mllib.common import JavaModelWrapper, callMLlibFunc, _to_java_object_rdd

__all__ = ['MatrixFactorizationModel', 'ALS']


class Rating(object):
    def __init__(self, user, product, rating):
        self.user = int(user)
        self.product = int(product)
        self.rating = float(rating)

    def __reduce__(self):
        return Rating, (self.user, self.product, self.rating)

    def __repr__(self):
        return "Rating(%d, %d, %d)" % (self.user, self.product, self.rating)


class MatrixFactorizationModel(JavaModelWrapper):

    """A matrix factorisation model trained by regularized alternating
    least-squares.

    >>> r1 = (1, 1, 1.0)
    >>> r2 = (1, 2, 2.0)
    >>> r3 = (2, 1, 2.0)
    >>> ratings = sc.parallelize([r1, r2, r3])
    >>> model = ALS.trainImplicit(ratings, 1)
    >>> model.predict(2,2) is not None
    True

    >>> testset = sc.parallelize([(1, 2), (1, 1)])
    >>> model = ALS.train(ratings, 1)
    >>> model.predictAll(testset).count() == 2
    True

    >>> model = ALS.train(ratings, 4)
    >>> model.userFeatures().count() == 2
    True

    >>> first_user = model.userFeatures().take(1)[0]
    >>> latents = first_user[1]
    >>> len(latents) == 4
    True

    >>> model.productFeatures().count() == 2
    True

    >>> first_product = model.productFeatures().take(1)[0]
    >>> latents = first_product[1]
    >>> len(latents) == 4
    True
    """
    def predict(self, user, product):
        return self._java_model.predict(user, product)

    def predictAll(self, user_product):
        assert isinstance(user_product, RDD), "user_product should be RDD of (user, product)"
        first = user_product.first()
        assert len(first) == 2, "user_product should be RDD of (user, product)"
        user_product = user_product.map(lambda (u, p): (int(u), int(p)))
        return self.call("predict", user_product)

    def userFeatures(self):
        return self.call("getUserFeatures")

    def productFeatures(self):
        return self.call("getProductFeatures")


class ALS(object):

    @classmethod
    def _prepare(cls, ratings):
        assert isinstance(ratings, RDD), "ratings should be RDD"
        first = ratings.first()
        if not isinstance(first, Rating):
            if isinstance(first, (tuple, list)):
                ratings = ratings.map(lambda x: Rating(*x))
            else:
                raise ValueError("rating should be RDD of Rating or tuple/list")
        return _to_java_object_rdd(ratings, True)

    @classmethod
    def train(cls, ratings, rank, iterations=5, lambda_=0.01, blocks=-1):
        model = callMLlibFunc("trainALSModel", cls._prepare(ratings), rank, iterations,
                              lambda_, blocks)
        return MatrixFactorizationModel(model)

    @classmethod
    def trainImplicit(cls, ratings, rank, iterations=5, lambda_=0.01, blocks=-1, alpha=0.01):
        model = callMLlibFunc("trainImplicitALSModel", cls._prepare(ratings), rank,
                              iterations, lambda_, blocks, alpha)
        return MatrixFactorizationModel(model)


def _test():
    import doctest
    import pyspark.mllib.recommendation
    globs = pyspark.mllib.recommendation.__dict__.copy()
    globs['sc'] = SparkContext('local[4]', 'PythonTest', batchSize=2)
    (failure_count, test_count) = doctest.testmod(globs=globs, optionflags=doctest.ELLIPSIS)
    globs['sc'].stop()
    if failure_count:
        exit(-1)


if __name__ == "__main__":
    _test()

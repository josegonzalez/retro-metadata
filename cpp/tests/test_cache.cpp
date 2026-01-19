// Tests for cache system functionality
#include <gtest/gtest.h>

#include <chrono>
#include <retro_metadata/cache/memory.hpp>
#include <thread>

#include "testutil/loader.hpp"

using namespace retro_metadata;
using namespace retro_metadata::testutil;
using namespace retro_metadata::cache;

class CacheTest : public ::testing::Test {
  protected:
    void SetUp() override { loader_ = std::make_unique<Loader>(Loader::from_compile_definition()); }

    std::unique_ptr<Loader> loader_;
};

// Test memory cache using shared test data
TEST_F(CacheTest, MemoryCacheOperations) {
    auto test_cases = loader_->get_test_cases("cache", "memory_cache");
    // Note: These test cases may describe sequences of operations
    // We'll implement direct tests below

    MemoryCache cache(100, std::chrono::minutes(5));

    // Basic set and get
    cache.set("key1", "value1");
    auto result = cache.get("key1");
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(*result, "value1");

    // Get non-existent key
    result = cache.get("nonexistent");
    EXPECT_FALSE(result.has_value());
}

// Direct unit tests for MemoryCache
TEST_F(CacheTest, SetAndGet) {
    MemoryCache cache(100, std::chrono::minutes(5));

    cache.set("test_key", "test_value");
    auto value = cache.get("test_key");

    ASSERT_TRUE(value.has_value());
    EXPECT_EQ(*value, "test_value");
}

TEST_F(CacheTest, GetNonExistent) {
    MemoryCache cache(100, std::chrono::minutes(5));

    auto value = cache.get("nonexistent_key");
    EXPECT_FALSE(value.has_value());
}

TEST_F(CacheTest, Overwrite) {
    MemoryCache cache(100, std::chrono::minutes(5));

    cache.set("key", "value1");
    cache.set("key", "value2");

    auto value = cache.get("key");
    ASSERT_TRUE(value.has_value());
    EXPECT_EQ(*value, "value2");
}

TEST_F(CacheTest, Remove) {
    MemoryCache cache(100, std::chrono::minutes(5));

    cache.set("key", "value");
    EXPECT_TRUE(cache.exists("key"));

    cache.remove("key");
    EXPECT_FALSE(cache.exists("key"));
    EXPECT_FALSE(cache.get("key").has_value());
}

TEST_F(CacheTest, Exists) {
    MemoryCache cache(100, std::chrono::minutes(5));

    EXPECT_FALSE(cache.exists("key"));
    cache.set("key", "value");
    EXPECT_TRUE(cache.exists("key"));
}

TEST_F(CacheTest, Clear) {
    MemoryCache cache(100, std::chrono::minutes(5));

    cache.set("key1", "value1");
    cache.set("key2", "value2");
    cache.set("key3", "value3");

    EXPECT_TRUE(cache.exists("key1"));
    EXPECT_TRUE(cache.exists("key2"));
    EXPECT_TRUE(cache.exists("key3"));

    cache.clear();

    EXPECT_FALSE(cache.exists("key1"));
    EXPECT_FALSE(cache.exists("key2"));
    EXPECT_FALSE(cache.exists("key3"));
}

TEST_F(CacheTest, Stats) {
    MemoryCache cache(100, std::chrono::minutes(5));

    cache.set("key1", "value1");
    cache.set("key2", "value2");

    // Hit
    cache.get("key1");
    cache.get("key2");

    // Miss
    cache.get("nonexistent");

    auto stats = cache.stats();
    EXPECT_EQ(stats.size, 2u);
    EXPECT_EQ(stats.hits, 2u);
    EXPECT_EQ(stats.misses, 1u);
}

TEST_F(CacheTest, LRUEviction) {
    // Create cache with max size of 3
    MemoryCache cache(3, std::chrono::minutes(5));

    cache.set("key1", "value1");
    cache.set("key2", "value2");
    cache.set("key3", "value3");

    // All keys should exist
    EXPECT_TRUE(cache.exists("key1"));
    EXPECT_TRUE(cache.exists("key2"));
    EXPECT_TRUE(cache.exists("key3"));

    // Access key1 to make it recently used
    cache.get("key1");

    // Add key4, which should evict key2 (least recently used)
    cache.set("key4", "value4");

    EXPECT_TRUE(cache.exists("key1"));   // Recently accessed
    EXPECT_FALSE(cache.exists("key2"));  // Should be evicted
    EXPECT_TRUE(cache.exists("key3"));
    EXPECT_TRUE(cache.exists("key4"));
}

TEST_F(CacheTest, TTLExpiration) {
    // Create cache with 100ms TTL
    MemoryCache cache(100, std::chrono::milliseconds(100));

    cache.set("key", "value");
    EXPECT_TRUE(cache.exists("key"));

    // Wait for TTL to expire
    std::this_thread::sleep_for(std::chrono::milliseconds(150));

    // Key should be expired
    auto value = cache.get("key");
    EXPECT_FALSE(value.has_value());
}

TEST_F(CacheTest, Close) {
    MemoryCache cache(100, std::chrono::minutes(5));

    cache.set("key", "value");
    cache.close();

    // After close, cache should be empty
    EXPECT_FALSE(cache.exists("key"));
}

TEST_F(CacheTest, ThreadSafety) {
    MemoryCache cache(1000, std::chrono::minutes(5));

    const int num_threads = 4;
    const int ops_per_thread = 100;

    std::vector<std::thread> threads;

    for (int t = 0; t < num_threads; ++t) {
        threads.emplace_back([&cache, t, ops_per_thread]() {
            for (int i = 0; i < ops_per_thread; ++i) {
                std::string key = "thread" + std::to_string(t) + "_key" + std::to_string(i);
                std::string value = "value" + std::to_string(i);
                cache.set(key, value);
                cache.get(key);
            }
        });
    }

    for (auto& thread : threads) {
        thread.join();
    }

    // Verify some entries exist
    EXPECT_TRUE(cache.stats().size > 0);
}

TEST_F(CacheTest, EmptyKeyAndValue) {
    MemoryCache cache(100, std::chrono::minutes(5));

    // Empty key
    cache.set("", "value");
    auto result = cache.get("");
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(*result, "value");

    // Empty value
    cache.set("key", "");
    result = cache.get("key");
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(*result, "");
}

TEST_F(CacheTest, LargeValues) {
    MemoryCache cache(100, std::chrono::minutes(5));

    // Create a large string (1MB)
    std::string large_value(1024 * 1024, 'x');

    cache.set("large_key", large_value);
    auto result = cache.get("large_key");

    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->size(), large_value.size());
}
